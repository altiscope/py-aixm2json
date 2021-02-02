# AixM To Json

## KickStart

### Requirements

- Python 3.8.5 
- Pip 19.2.3
- VirtualEnv 16.7.7 (_foo@bar~\$> pip install virtualenv_)
- GDAL 2.3.3

### Commands to execute

#### To run

```bash
foo@bar~$> python aixm2json.py -i foo/input_aixm_file.xml -o foo/output_geojson_dir/
```

#### To create and configure the virtualenv

```bash
foo@bar~$> virtualenv venv
```

##### In Windows

```bash
py-billing> venv\Scripts\activate
(venv) py-billing> pip install -r requirements.txt
```

##### In Linux

```bash
foo@bar py-billing$> source env/bin/activate
(venv) foo@bar py-billing$> pip install -r requirements.txt
```

#### In Docker with GDAL
- Docker image osgeo/gdal:alpine-normal-latest
- Downloaded from: https://github.com/OSGeo/gdal/tree/master/gdal/docker

#### GDAL Library

```bash
foo@bar~$> yum-config-manager --enable epel
foo@bar~$> yum -y install make automake gcc gcc-c++ libcurl-devel proj-devel geos-devel
foo@bar~$> cd /usr/src/
foo@bar~$> curl -L http://download.osgeo.org/gdal/2.3.0/gdal-2.3.0.tar.gz | tar zxf -
foo@bar~$> curl -L http://download.osgeo.org/gdal/2.3.3/gdal-2.3.3.tar.gz | tar zxf -
foo@bar~$> cd gdal-2.3.0/
foo@bar~$> cd gdal-2.3.3/
foo@bar~$> ./configure --prefix=/usr/local --without-python
foo@bar~$> make -j4
foo@bar~$> make install
foo@bar~$> cd /usr/local
foo@bar~$> tar zcvf ~/gdal-2.3.0-amz1.tar.gz *

