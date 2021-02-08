import re
import getopt
import json
import sys
from osgeo import ogr, gdal
from geojson import Point

input_path = ''
output_path = ''
open_options = ['XSD=schemas/aixm_5_1_1_xsd/message/AIXM_BasicMessage.xsd',
                'EMPTY_AS_NULL=YES',
                'FORCE_SRS_DETECTION=NO',
                'READ_MODE=AUTO',
                'CONSIDER_EPSG_AS_URN=AUTO',
                'GML_ATTRIBUTES_TO_OGR_FIELDS=NO',
                'INVERT_AXIS_ORDER_IF_LAT_LONG=YES',
                'SWAP_COORDINATES=AUTO']

def load_aixm():
    print('Loading file')
    gdal.SetConfigOption('GML_SKIP_CORRUPTED_FEATURES', 'YES')
    gdal_data_source = gdal.OpenEx(input_path, nOpenFlags=0, open_options=open_options)
    print('Loaded file')

    for i in range(gdal_data_source.GetLayerCount()):
        layer = gdal_data_source.GetLayer(i)
        layer_definition = layer.GetLayerDefn()
        layer_name = layer.GetName()
        # print('Reading layers', layer_name)
        field_list = []

        for j in range(layer_definition.GetFieldCount()):
            field_name = layer_definition.GetFieldDefn(j).GetName()
            field_list.append(field_name)

        feature_num = layer.GetFeatureCount()

        # TODO: We should change to Python Object.
        feature_list = [{'properties': None} for k in range(feature_num)]

        feature_count = 0
        for feature in layer:
            for field in field_list:
                # print('Reading field', field)
                value = feature.GetField(field)
                if layer_name == "Airspace" and field == 'identifier':
                    print(value)
                if feature_list[feature_count]['properties'] is None:
                    feature_list[feature_count]['properties'] = {field: value}
                else:
                    feature_list[feature_count]['properties'][field] = value
            if feature.GetGeometryRef() is not None:
                if feature.GetGeometryRef().ExportToJson() is None:
                    g1 = ogr.CreateGeometryFromWkt(str(feature.GetGeometryRef()))
                    g1l = g1.GetLinearGeometry()
                    feature_list[feature_count]['geometry'] = json.loads(g1l.ExportToJson())
                else:
                    feature_list[feature_count]['geometry'] = json.loads(feature.GetGeometryRef().ExportToJson())
            else:
                if layer_name == "Airspace":
                    print("can't get geometry")
            feature_count += 1

        geojson = {'type': 'FeatureCollection', 'features': feature_list}
        with open(output_path + '/' + layer_name + '.json', 'w', encoding='utf-8') as file:
            json.dump(geojson, file, ensure_ascii=False, indent=4)

def fix_airspace_geojson():
    with open(output_path + '/Airspace.json') as f:
        data = json.load(f)

    for feature in data['features']:
        # geojson viewer throws an error of a polygon is not closed
        # so we need to make sure that the first and last set of coordinates are the same
        try:
            last_coordinate_position = len(feature['geometry']['coordinates'][0]) - 1
            # if the last coordinate is not the same as the first, add a new one that is!
            if feature['geometry']['coordinates'][0][last_coordinate_position] != feature['geometry']['coordinates'][0][0]:
                feature['geometry']['coordinates'][0][last_coordinate_position + 1] = feature['geometry']['coordinates'][0][0]
        except:
            print("something went wrong")

    with open(output_path + '/Airspace.json', 'w') as file:
        json.dump(data, file, indent=2)

def fix_airport_heliport_geojson():
    with open(output_path + '/AirportHeliport.json') as f:
        data = json.load(f)

    for feature in data['features']:
        # the AirportHeliport feature position property is not read as a geometry by ogr
        # so we need to create a geometric point based on the position data
        # get lat/lon out of the 'pos' data
        print(feature)
        if feature['properties']['pos']:
            coords = feature['properties']['pos'].split(" ")
            lat = coords[1]
            lon = coords[0]
        # create point geometry (lon comes before lat in the pos element, so we need to reverse for a point)
            my_point = Point((float(lat), float(lon)))
            feature['geometry'] = my_point

    
        
    with open(output_path + '/AirportHeliport.json', 'w') as file:
        json.dump(data, file, indent=2)


def get_arguments(argv):
    help_message = 'aixm2json.py -i <aixm_input_file> -o <geojson_output_path>'
    try:
        opts, args = getopt.getopt(argv, "i:o:", ["input=", "output="])
    except getopt.GetoptError:
        print(help_message)
        sys.exit(2)

    if len(opts) < 2:
        print(help_message)
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print(help_message)
            sys.exit()
        elif opt in ("-i", "--input"):
            global input_path
            input_path = arg
        elif opt in ("-o", "--output"):
            global output_path
            output_path = arg


if __name__ == '__main__':
    get_arguments(sys.argv[1:])
    load_aixm()
    fix_airspace_geojson()
    # fix_airport_heliport_geojson()
