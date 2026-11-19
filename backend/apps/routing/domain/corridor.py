from dataclasses import dataclass
from math import atan2, ceil, cos, hypot, radians, sin, degrees

from geographiclib.geodesic import Geodesic
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from .errors import RoutingError
from .geometry import METERS_PER_MILE, validate_coordinate
from .route_models import Coordinate
from .validation import require_positive


@dataclass(frozen=True)
class CorridorCell:
    id: str
    coordinate: Coordinate
    geometry: dict


@dataclass(frozen=True)
class CorridorGrid:
    cells: tuple[CorridorCell, ...]
    boundary: dict
    center: Coordinate
    buffer_miles: float
    requested_spacing_miles: float
    spacing_miles: float

    @property
    def coarsened(self):
        return self.spacing_miles > self.requested_spacing_miles


@dataclass(frozen=True)
class LocalProjection:
    center: Coordinate

    def forward(self, coordinate):
        lon, lat = coordinate
        result = Geodesic.WGS84.Inverse(self.center[1], self.center[0], lat, lon)
        bearing = radians(result["azi1"])
        return sin(bearing) * result["s12"], cos(bearing) * result["s12"]

    def inverse(self, x, y, *, unwrap=False):
        result = Geodesic.WGS84.Direct(self.center[1], self.center[0], degrees(atan2(x, y)), hypot(x, y))
        longitude = result["lon2"]
        if unwrap:
            longitude = self.center[0] + ((longitude - self.center[0] + 180) % 360 - 180)
        return longitude, result["lat2"]


def _center(coordinates):
    longitudes = sorted({point[0] % 360 for point in coordinates})
    gaps = [(longitudes[(i + 1) % len(longitudes)] + (360 if i == len(longitudes)-1 else 0) - value, i)
            for i, value in enumerate(longitudes)]
    gap, index = max(gaps)
    start = longitudes[(index + 1) % len(longitudes)]
    longitude = (start + (360 - gap) / 2 + 180) % 360 - 180
    latitude = (min(point[1] for point in coordinates) + max(point[1] for point in coordinates)) / 2
    return longitude, latitude


def _polygons(geometry):
    if isinstance(geometry, Polygon):
        return [geometry] if not geometry.is_empty else []
    if hasattr(geometry, "geoms"):
        return [polygon for part in geometry.geoms for polygon in _polygons(part)]
    return []


def _geographic_geometry(geometry, projection):
    output = []
    for polygon in _polygons(geometry):
        shell = [projection.inverse(x, y, unwrap=True) for x, y in polygon.exterior.coords]
        holes = [[projection.inverse(x, y, unwrap=True) for x, y in ring.coords] for ring in polygon.interiors]
        geographic = Polygon(shell, holes)
        for shift in (-360, 0, 360):
            piece = geographic.intersection(box(-180 + shift, -90, 180 + shift, 90))
            for part in _polygons(piece):
                if part.area > 0:
                    output.append(orient(affinity.translate(part, xoff=-shift), sign=1))
    if not output:
        raise RoutingError("invalid_corridor_geometry", "The corridor could not be represented geographically.")
    return mapping(output[0] if len(output) == 1 else MultiPolygon(output))


def build_corridor_grid(
    routes, *, buffer_miles=15, spacing_miles=10, max_cells=150,
    max_candidates=10000, max_vertices=50000, max_radius_km=2000,
) -> CorridorGrid:
    require_positive(buffer_miles, "Corridor buffer")
    require_positive(spacing_miles, "Corridor grid spacing")
    require_positive(max_radius_km, "Corridor projection radius")
    if min(max_cells, max_candidates, max_vertices) < 1:
        raise ValueError("Corridor resource limits must be positive.")
    routes = tuple(tuple(validate_coordinate(point) for point in route) for route in routes)
    if not routes or any(len(route) < 2 or len(set(route)) < 2 for route in routes):
        raise RoutingError("invalid_corridor_geometry", "Corridor routes need nonempty road geometry.")
    if sum(len(route) for route in routes) > max_vertices:
        raise RoutingError("corridor_too_large", "The route geometry exceeds the corridor processing limit.")
    coordinates = {point for route in routes for point in route}
    if any(abs(point[1]) > 85 for point in coordinates):
        raise RoutingError("corridor_too_large", "Corridor rendering supports route latitudes between -85 and 85 degrees.")
    center = _center(coordinates)
    projection = LocalProjection(center)
    projected = {point: projection.forward(point) for point in coordinates}
    if any(hypot(*point) > max_radius_km * 1000 for point in projected.values()):
        raise RoutingError("corridor_too_large", "The routes exceed the supported local corridor extent.")
    lines = [LineString([projected[point] for point in route]) for route in routes]
    corridor = unary_union([
        line.simplify(25, preserve_topology=True).buffer(buffer_miles * METERS_PER_MILE, quad_segs=4)
        for line in lines
    ]).simplify(10, preserve_topology=True)
    xmin, ymin, xmax, ymax = corridor.bounds
    spacing = spacing_miles * METERS_PER_MILE
    for _ in range(40):
        columns, rows = ceil((xmax - xmin) / spacing), ceil((ymax - ymin) / spacing)
        candidates = columns * rows
        if candidates > max_candidates:
            spacing *= 1.5
            continue
        cells = []
        for x in range(columns):
            for y in range(rows):
                square = box(xmin + x * spacing, ymin + y * spacing,
                             xmin + (x + 1) * spacing, ymin + (y + 1) * spacing)
                clipped = corridor.intersection(square)
                polygons = _polygons(clipped)
                if not polygons or sum(part.area for part in polygons) < 1:
                    continue
                clipped = unary_union(polygons)
                sample = clipped.representative_point()
                cells.append((projection.inverse(sample.x, sample.y), clipped))
                if len(cells) > max_cells:
                    break
            if len(cells) > max_cells:
                break
        if len(cells) > max_cells:
            spacing *= 1.5
            continue
        if not cells:
            raise RoutingError("invalid_corridor_geometry", "No geographic corridor cells could be sampled.")
        boundary = _geographic_geometry(corridor, projection)
        geographic_boundary = shape(boundary)
        geographic_cells = []
        for point, geometry in cells:
            clipped = shape(_geographic_geometry(geometry, projection)).intersection(geographic_boundary)
            polygons = [orient(part, sign=1) for part in _polygons(clipped) if part.area > 0]
            if not polygons:
                continue
            clipped = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
            if not clipped.covers(Point(point)):
                sample = clipped.representative_point()
                point = (sample.x, sample.y)
            geographic_cells.append(CorridorCell(f"cell-{len(geographic_cells):03d}", point, mapping(clipped)))
        if not geographic_cells:
            raise RoutingError("invalid_corridor_geometry", "No geographic corridor cells could be sampled.")
        return CorridorGrid(tuple(geographic_cells), boundary, center, buffer_miles,
                            spacing_miles, spacing / METERS_PER_MILE)
    raise RoutingError("corridor_too_large", "The corridor could not fit within the configured grid budget.")
