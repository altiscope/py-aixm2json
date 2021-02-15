
# from xml.etree.ElementTree import Element, SubElement, Comment, tostring
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
import lxml.etree as LET
from geospatial import Geo
from decimal import Decimal

input_file = 'aixm-testfiles/BR/05nov20v2.xml'
output_file = 'aixm-testfiles/BR/05nov20v2_processed.xml'
# input_file = 'aixm-testfiles/UK/WEF2021-01-28_EXP2021-02-01_CRC_171CB976.xml'
# output_file = 'aixm-testfiles/UK/WEF2021-01-28_EXP2021-02-01_CRC_171CB976_processed.xml'
# input_file = 'aixm-testfiles/UK/aixm-test.xml'
# output_file = 'aixm-testfiles/UK/aixm-test_processed.xml'


tree = ET.parse(input_file)
ltree = LET.parse(input_file)
root = tree.getroot()
lroot = ltree.getroot()
ET.register_namespace('gsr','http://www.isotc211.org/2005/gsr')
ET.register_namespace('gml','http://www.opengis.net/gml/3.2')
ET.register_namespace('gss','http://www.isotc211.org/2005/gss')
ET.register_namespace('gts','http://www.isotc211.org/2005/gts')
ET.register_namespace('aixm','http://www.aixm.aero/schema/5.1')
ET.register_namespace('xsi','http://www.w3.org/2001/XMLSchema-instance')
ET.register_namespace('adfe','http://www.idscorporation.com/adf/aixm51/ext')
ET.register_namespace('gco','http://www.isotc211.org/2005/gco')
ET.register_namespace('event','http://www.aixm.aero/schema/5.1/event')
ET.register_namespace('message', 'http://www.aixm.aero/schema/5.1/message')
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
ET.register_namespace('ADR', 'http://www.aixm.aero/schema/5.1/extensions/EUR/ADR')
ET.register_namespace('gml:id', 'uniqueId')
ET.register_namespace('gmd', 'http://www.isotc211.org/2005/gmd')
ET.register_namespace('null', 'http://www.w3.org/2001/XMLSchema')


for node in root.iter():

    # resolve airspace elements with link:href
    airspaces = root.findall(".//{http://www.aixm.aero/schema/5.1}Airspace")
    airspace_geometries = node.findall('.//{http://www.aixm.aero/schema/5.1}geometryComponent')
    if airspace_geometries is not None:
        for airspace_geometry in airspace_geometries:
            airspace_geometry_components = airspace_geometry.findall('.//{http://www.aixm.aero/schema/5.1}AirspaceGeometryComponent')
            for airspace_geometry_component in airspace_geometry_components:
                contributing_airspaces = airspace_geometry.findall('.//{http://www.aixm.aero/schema/5.1}contributorAirspace')
                if contributing_airspaces is not None:
                    for contributing_airspace in contributing_airspaces:
                        the_airspace = contributing_airspace.find('.//{http://www.aixm.aero/schema/5.1}theAirspace')
                        the_airspace_href = the_airspace.get("{http://www.w3.org/1999/xlink}href")
                        the_contributing_airspace_id = the_airspace_href.replace("urn:uuid:","uuid.")
                        print("Parent airspace geometry: " + str(airspace_geometry))
                
                        for airspace in airspaces:
                            airspace_id = airspace.get('{http://www.opengis.net/gml/3.2}id')
                            try:
                                if airspace_id == the_contributing_airspace_id:
                                    print("Airspace: " + str(airspace))
                                    print("Airspace id: " + airspace_id)
                                    print("Contributing airspace id: " + the_contributing_airspace_id)
                                    print(airspace.find('.//{http://www.aixm.aero/schema/5.1}AirspaceGeometryComponent'))
                                    airspace_geometry.remove(airspace_geometry_component)
                                    airspace_geometry.append(airspace.find('.//{http://www.aixm.aero/schema/5.1}AirspaceGeometryComponent'))
                            except:
                                "no bueno"

    # clean up ring geometries
    if node.tag == "{http://www.opengis.net/gml/3.2}Ring":

        # combine multiple curvemembers into a single one with one set of segments
        curveMembers = node.findall('.//{http://www.opengis.net/gml/3.2}curveMember')
        if len(curveMembers) > 1:
            finalCurveMember = Element("{http://www.opengis.net/gml/3.2}curveMember")
            finalCurve = Element("{http://www.opengis.net/gml/3.2}Curve")
            finalSegments = Element("{http://www.opengis.net/gml/3.2}segments")
            for curveMember in curveMembers:
                curveMemberSegments = curveMember.findall('.//{http://www.opengis.net/gml/3.2}Curve/{http://www.opengis.net/gml/3.2}segments')
                for segments in curveMemberSegments:
                    for child in segments:
                        finalSegments.append(child)
                node.remove(curveMember)
            finalCurve.append(finalSegments)
            finalCurveMember.append(finalCurve)    
            node.append(finalCurveMember)
                
        
        # replace ArcByCenterPoint with posList
        segments = node.findall('.//{http://www.opengis.net/gml/3.2}segments')
        for i in range(len(segments)):
            j = 0
            for item in segments[i]:
                # convert ArcByCenterPoint to GeodesicString
                if item.tag == '{http://www.opengis.net/gml/3.2}ArcByCenterPoint':
                    # get the center point
                    center = ""
                    if item.find('{http://www.opengis.net/gml/3.2}pointProperty'):
                        center = item.find('.//{http://www.opengis.net/gml/3.2}pointProperty/{http://www.aixm.aero/schema/5.1}Point/{http://www.opengis.net/gml/3.2}pos').text.split()
                    else:
                        center = item.find('{http://www.opengis.net/gml/3.2}pos').text.split()

                    # set lat/lon in decimal format
                    center_lon = Decimal('{0:.6f}'.format(float(center[0])))
                    center_lat = Decimal('{0:.6f}'.format(float(center[1])))
                    center = [center_lat, center_lon]

                    # get the start and end angles
                    start_angle = float(item.find('{http://www.opengis.net/gml/3.2}startAngle').text)
                    end_angle = float(item.find('{http://www.opengis.net/gml/3.2}endAngle').text)

                    # get the radius and calculate normalize to kilometers
                    radius_element = item.find('{http://www.opengis.net/gml/3.2}radius')
                    radius_uom = radius_element.attrib['uom']
                    radius = float(radius_element.text)
                    # if uom is nautical miles, get kilometers
                    if radius_uom == "[nmi_i]":
                        radius = radius * 1.852

                    # ISO 19107 "Thus, if the start angle of an ArcByCenterPoint in this CRS is smaller 
                    # than its end angle, then the direction of the arc is counter-clockwise; 
                    # otherwise it is clockwise."
                    clockwise = True
                    # if start_angle < end_angle:
                    #     clockwise = False

                    # generate positions for the GeodesicString
                    positions = Geo.arc_from_bearing(center, radius, start_angle, end_angle, clockwise)

                    # create GeodesicString element to replace arc
                    geodesicstring = Element("{http://www.opengis.net/gml/3.2}GeodesicString")
                    posList = Element("{http://www.opengis.net/gml/3.2}posList")
                    k = 0
                    while k < len(positions):
                        lat = str(positions[k][0])
                        lon = str(positions[k][1])
                        if k == 0:
                            posList.text = lon + " " + lat
                        else:
                            posList.text = posList.text + " " + lon + " " + lat
                        k += 1
                    geodesicstring.append(posList)

                    # remove ArcByCenterPoint element
                    segments[i].remove(item)

                    # insert GeodesicString where the ArcByCenterPoint element used to be
                    segments[i].insert(j, geodesicstring)
                j += 1

            # make sure the segment pieces connect to each other and that the polygon is closed
            segment_pieces = list(segments[i])
            k=0
            first_position = ""
            prior_segment_end_position = ""

            while k < len(segment_pieces):
                if segment_pieces[k].find('{http://www.opengis.net/gml/3.2}pointProperty') is not None:
                    positions = segment_pieces[k].findall('.//{http://www.opengis.net/gml/3.2}pointProperty/{http://www.aixm.aero/schema/5.1}Point/{http://www.opengis.net/gml/3.2}pos')

                    # set first position
                    if k == 0:
                        first_position = positions[0].text
                    
                    # swap first position in the segment piece with the last position of the prior segment piece
                    if prior_segment_end_position != "":
                        positions[0].text = prior_segment_end_position

                    # set last position
                    prior_segment_end_position = positions[len(positions) - 1].text
                    
                    # closing the polygon
                    if k == len(segment_pieces) - 1:
                        positions[len(positions)-1].text = first_position

                if segment_pieces[k].find('{http://www.opengis.net/gml/3.2}posList') is not None:
                    posList = segment_pieces[k].find('{http://www.opengis.net/gml/3.2}posList')
                    positions = posList.text.split(" ")

                    # set first position
                    if k == 0:
                        first_position = positions[0] + " " + positions[1]

                    # swap first position in the segment piece with the last position of the prior segment piece
                    if prior_segment_end_position != "":
                        posList.text = prior_segment_end_position + " " + posList.text

                    # set new last position
                    prior_segment_end_position = positions[len(positions) - 2] + " " + positions[len(positions) - 1]

                    # closing the polygon
                    if k == len(segment_pieces) - 1:
                        posList.text = posList.text + " " + first_position

                k += 1

tree.write(open(output_file, 'w'), encoding='unicode', xml_declaration=True, method="xml")

# ogr2ogr -f "GeoJSON" airport-heliport.geojson airport_heliport.xml -skipfailures -nlt POINT -geomfield ARP9