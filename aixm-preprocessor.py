import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from geospatial import Geo
from decimal import Decimal

# from trace import traceit
# # from xml.dom import minidom

# doc = xml.dom.minidom.parse("05nov20v2.xml")
# airspace = doc.getElementsByTagName("aixm:Airspace")
# airport_heliport = doc.getElementsByTagName("aixm:AirportHeliport")

# brAirspace = xml.dom.minidom.Document()
# xml = brAirspace.createElement('message:AIXMBasicMessage')
# xml.setAttribute("gml:id", "uniqueId")
# xml.setAttribute("xmlns:gss", "http://www.isotc211.org/2005/gss")
# xml.setAttribute("xmlns:gts", "http://www.isotc211.org/2005/gts")
# xml.setAttribute("xmlns:gsr", "http://www.isotc211.org/2005/gsr")
# xml.setAttribute("xmlns:gml", "http://www.opengis.net/gml/3.2")
# xml.setAttribute("xmlns:message", "http://www.aixm.aero/schema/5.1/message")
# xml.setAttribute("xmlns:adr", "http://www.aixm.aero/schema/5.1/extensions/EUR/ADR")
# xml.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
# xml.setAttribute("xmlns:adfe", "http://www.idscorporation.com/adf/aixm51/ext")
# xml.setAttribute("xmlns:aixm", "http://www.aixm.aero/schema/5.1")
# xml.setAttribute("xmlns:gco", "http://www.isotc211.org/2005/gco")
# xml.setAttribute("xmlns:event", "http://www.aixm.aero/schema/5.1/event")
# xml.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink")
# xml.setAttribute("xmlns:gmd", "http://www.isotc211.org/2005/gmd")


# i=0
# while i < len(airspace):
# 	message = brAirspace.createElement('message:hasMember')
# 	message.appendChild(airspace.item(i))
# 	xml.appendChild(message)
# 	i += 1

# xml_str_airspace = xml.toprettyxml(indent="\t") 

# save_path_file_airspace = "airspace.xml"

# with open(save_path_file_airspace, "w") as f: 
# 	f.write(xml_str_airspace)

# ogr2ogr -f "GeoJSON" airspace.geojson airspace.xml -skipfailures


tree = ET.parse('aixm-testfiles/UK/WEF2021-01-28_EXP2021-02-01_CRC_171CB976.xml')
root = tree.getroot()
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
    # clean up ring geometries
    if node.tag == "{http://www.opengis.net/gml/3.2}Ring":

        # resolve elements with link:href
        for child in node:
            if child.get('{http://www.w3.org/1999/xlink}href'):
                # need to figure out how to resolve these
                node.remove(child)
        
        segments = node.findall('.//{http://www.opengis.net/gml/3.2}segments')
        for i in range(len(segments)):

            # convert arcbycenterpoint to position list
            arcs = segments[i].findall('.//{http://www.opengis.net/gml/3.2}ArcByCenterPoint')
            if arcs is not None:
                j = 0
                while j in range(len(arcs)):
                    # get the data
                    center = ""
                    if arcs[j].find('{http://www.opengis.net/gml/3.2}pointProperty'):
                        center = arcs[j].find('.//{http://www.opengis.net/gml/3.2}pointProperty/{http://www.aixm.aero/schema/5.1}Point/{http://www.opengis.net/gml/3.2}pos').text.split()
                    else:
                        center = arcs[j].find('{http://www.opengis.net/gml/3.2}pos').text.split()
                    start_angle = float(arcs[j].find('{http://www.opengis.net/gml/3.2}startAngle').text)
                    end_angle = float(arcs[j].find('{http://www.opengis.net/gml/3.2}endAngle').text)
                    radius_element = arcs[j].find('{http://www.opengis.net/gml/3.2}radius')
                    radius_uom = radius_element.attrib['uom']
                    radius = float(radius_element.text)
                    # if uom is nautical miles, get kilometers
                    if radius_uom == "[nmi_i]":
                        radius = radius * 1.852

                    # gml:pos - lat lon
                    # geojson coordinates - lon, lat

                    center_lon = Decimal('{0:.6f}'.format(float(center[0])))
                    center_lat = Decimal('{0:.6f}'.format(float(center[1])))
                    center = [center_lat, center_lon]

                    # ISO 19107 "Thus, if the start angle of an ArcByCenterPoint in this CRS is smaller 
                    # than its end angle, then the direction of the arc is counter-clockwise; 
                    # otherwise it is clockwise."
                    clockwise = True
                    # if start_angle < end_angle:
                    #     clockwise = False

                    positions = Geo.arc_from_bearing(center, radius, start_angle, end_angle, clockwise)

                    # create geodesic string to replace arc
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

                    # replace arc with geodesic string
                    segments[i].append(geodesicstring)
                    segments[i].remove(arcs[j])
                    # segments[i].replace(arcs[j],geodesicstring)
                    j += 1

        # fix posList so that each list connects to the one before it
        posList = node.findall('.//{http://www.opengis.net/gml/3.2}GeodesicString/{http://www.opengis.net/gml/3.2}posList')
        for i in range(len(posList)):
            # make sure the position lists are connected 
            # (last point in the posList is the same as the first point int he next posList)
            for j in range(i + 1, len(posList)):
                posI = posList[i].text.split(" ")
                posJ = posList[j].text.split(" ")
                posJ[0] = posI[len(posI) - 2]
                posJ[1] = posI[len(posI) - 1]


                s = " "
                posList[j].text = s.join(posJ)

tree.write(open('aixm-testfiles/UK/WEF2021-01-28_EXP2021-02-01_CRC_171CB976_processed.xml', 'w'), encoding='unicode', xml_declaration=True, method="xml")

# ogr2ogr -f "GeoJSON" airport-heliport.geojson airport_heliport.xml -skipfailures -nlt POINT -geomfield ARP9