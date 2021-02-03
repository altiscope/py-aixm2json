import json
import jsonlines
import math
import pyproj
from decimal import Decimal
from functools import partial
from geopy.distance import distance
from geopy.point import Point as GeoPoint
from pathlib import Path
from shapely.geometry import LineString, mapping, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import transform

# from trace import traceit
# use pyproj to get the right projection (spherical vs. cartesian)


class Geo(object):
    METERS_PER_NAUTICAL_MILE = 1852
    KILOMETERS_PER_NAUTICAL_MILE = 1.852
    FEET_PER_METER = 3.28084
    METER_PER_FOOT = 1.0 / FEET_PER_METER

    
    def geojson2shapely(geometry):
        """ Create a Shapely object from a GeoJSON geometry """
        if geometry.get('type') == 'LineString':
            return LineString(geometry['coordinates'])
        elif geometry.get('type') == 'Polygon':
            return Polygon(*geometry['coordinates'])

    
    def dms2dd_single(degrees, minutes, seconds, direction):
        """ Convert a single degrees/minutes/seconds value to decimal degree """
        dd = float(degrees) + float(minutes)/60 + float(seconds)/(60*60);
        if direction == 'W' or direction == 'S':
            dd *= -1
        return dd

    
    def to_geojson(poly=None, point=None, radius=None, geometry=None, properties={}):
        """ Generates pseudo-geojson for an object
            @param poly a Shapely polygon
            @param point a tuple in the form of (long, lat)
            @param radius in nautical miles
            @properties the properties array for the geojson
        """
        g = {
            "type": "Feature",
            "geometry": None,
            "properties": properties,
        }
        if poly:
            g['geometry'] = mapping(poly)
        elif geometry:
            g['geometry'] = geometry
        elif point and radius:
            g['geometry'] = {
                'type': 'Polygon',
                'coordinates': [Geo.circle(point, radius)]
            }
        return g

    def arc_from_bearing(center, radius, bearingA, bearingB, clockwise = True, resolution = 256):
        """
        Generate coordinates that approximate an arc between pointA and pointB
        from a circle centered at center with radius in nautical miles.
        """
        coords = []
        center_pt = GeoPoint(longitude=center[0], latitude=center[1])
        diff = bearingB - bearingA
        # if diff < 0:
        #     diff = 360 - diff
        sign = 1 if clockwise else -1
        for i in range(1,resolution):
            bearing = bearingA + sign*float(diff)*i/resolution
            d = distance(radius)
            v = d.destination(center_pt, bearing)
            coords.append((Decimal('{0:.6f}'.format(v.longitude)), Decimal('{0:.6f}'.format(v.latitude))))
        return coords


    
    def arc(center, radius, pointA, pointB, clockwise = True, resolution = 256):
        """
        Generate coordinates that approximate an arc between pointA and pointB
        from a circle centered at center with radius in nautical miles.
        """
        coords = []
        # radius = radius * Geo.METERS_PER_NAUTICAL_MILE
        bearingA = Geo.bearing(center, pointA)
        bearingB = Geo.bearing(center, pointB)
        center_pt = GeoPoint(longitude=center[0], latitude=center[1])
        diff = bearingB - bearingA
        # if diff < 0:
        #     diff = 360 - diff
        sign = 1 if clockwise else -1
        for i in range(1,resolution):
            bearing = bearingA + sign*float(diff)*i/resolution
            d = distance(radius)
            v = d.destination(center_pt, bearing)
            coords.append((Decimal('{0:.6f}'.format(v.longitude)), Decimal('{0:.6f}'.format(v.latitude))))
        return coords

    
    def buffer_wgs84(shape, radius, resolution = 128):
        """
        Buffer a Shapely Point, LineString or Polygon by "radius" meters
        """
        center = None
        if type(shape) is Point:
            center = shape
        else:
            center = shape.centroid
        wgs84_globe = pyproj.Proj(proj='latlong', ellps='WGS84')
        aeqd_local = pyproj.Proj(proj='aeqd', ellps='WGS84', datum='WGS84', lat_0=center.y, lon_0=center.x)
        projected_aeqd = transform(partial(pyproj.transform, wgs84_globe, aeqd_local), shape)
        polygon = projected_aeqd.buffer(radius, resolution=resolution)
        unprojected_wgs84 = transform(partial(pyproj.transform, aeqd_local, wgs84_globe), polygon)
        return orient(unprojected_wgs84, sign=1.0)

    
    def circle(center, radius):
        """
        Generate coordinates that approximate a circle
        centered at center with radius in nautical miles.
        """
        radius = radius * Geo.METERS_PER_NAUTICAL_MILE
        polygon = Geo.buffer_wgs84(Point(center), radius)
        return list(polygon.exterior.coords)

    
    def linestring_poly(points, radius, unit_nm=True, list_format=True):
        """
        Generate a polygon (usually rounded rectangle) from a LineString
        using a radius (default Nautical Miles, else meters) from the line
        """
        if unit_nm:
            radius = radius * Geo.METERS_PER_NAUTICAL_MILE
        line = LineString(points)
        polygon = Geo.buffer_wgs84(line, radius, resolution=10)
        if list_format:
            return list(polygon.exterior.coords)
        return mapping(polygon)

    def point_from_angle(point, distance, bearing):
        """
        Computes a new Shapely point that is distance away from point at angle in degrees

        **NOTE:** This function uses cartesian angles (where 0 degrees is "east" pointing).
        Please convert bearings (where 0 degrees is "north") with (90 - bearing) % 360
        before using this function.

        Args:
            point (shapely.geometry.Point)
            distance (float)
            bearing (float)
        
        Returns:
            Shapely Point
        """
        radians = math.radians(bearing)
        x = point.x + (distance * math.cos(radians))
        y = point.y + (distance * math.sin(radians))
        return Point(x, y)

    
    def bearing(pointA, pointB):
        """
        Calculates the bearing between two points.
        The formulae used is the following:
            θ = atan2(sin(Δlong).cos(lat2),
                      cos(lat1).sin(lat2) − sin(lat1).cos(lat2).cos(Δlong))
        :Parameters:
          - `pointA: The tuple representing the (longitude, latitude) for the
            first point. Latitude and longitude must be in decimal degrees
          - `pointB: The tuple representing the (longitude, latitude) for the
            second point. Latitude and longitude must be in decimal degrees
        :Returns:
          The bearing in degrees
        :Returns Type:
          float
        """
        lat1 = math.radians(float(pointA[1]))
        lat2 = math.radians(float(pointB[1]))

        diffLong = math.radians(float(pointB[0]) - float(pointA[0]))

        x = math.sin(diffLong) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
                * math.cos(lat2) * math.cos(diffLong))

        initial_bearing = math.atan2(x, y)

        # Now we have the initial bearing but math.atan2 return values
        # from -180° to + 180° which is not what we want for a compass bearing
        # The solution is to normalize the initial bearing as shown below
        initial_bearing = math.degrees(initial_bearing)
        compass_bearing = (initial_bearing + 360) % 360

        return compass_bearing

    
    def geojson_to_lines(geo_path: Path):
        """ Convert a GeoJSON FeatureCollection file to GeoJSONlines format
        """
        assert geo_path.suffix.lower() == '.geojson'
        out_path = geo_path.with_suffix('.geojsonl')
        with open(geo_path, 'r') as geojson_file, jsonlines.open(out_path, 'w', compact=True) as lines:
            data = json.load(geojson_file)
            for feature in data.get('features', []):
                lines.write(feature)
        return out_path

    
    def lines_to_geojson(geo_path: Path):
        """ Convert a GeoJSONlines file to GeoJSON FeatureCollection format
        """
        assert geo_path.suffix.lower() == '.geojsonl'
        out_path = geo_path.with_suffix('.geojson')
        with jsonlines.open(geo_path, 'r') as lines, open(out_path, 'w') as geojson_file:
            collection = {'type': 'FeatureCollection', 'features': []}
            for feature in lines:
                collection['features'].append(feature)
            json.dump(collection, geojson_file)
        return out_path