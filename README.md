# discomap.ServiceBackupTool
Backup Services from Servers

Description
This tool allows making a backup of the selected services from a server.

Environment requirements
The tool is developped to run under Arcgis 10.2 (Python2.7)
The ArcGIS services sources must be placed in a path according to the following structure: \\server_name\x\arcgisserver\...
The user that executes the tool or/and the user from ArcGIS Server that uses the geoprocessing service, should be able to access to each network path where the service’s sources are placed in order to copy them. 
The server where the geoprocessing service is displayed or the one where the tool is executed requires space to store a copy of all the sources of the migrated services.

Installation
ArcGIS Tool
ArcGis tool is placed in the toolbox called “Backup Services”. There is located the “BackupServices” tool.

 

Functionality

The script uses six parameters. All of them are mandatory:
 [1] Server Name (string)
The host name of the server. Typically a single name or fully qualified server, such as myServer.esri.com
 [2] Server Port (string)
The port number for the ArcGIS Server. Typically this is 6080. If you have a web adapter installed with your GIS Server and have the REST Admin enabled you can connect using the web servers port number.
[3] Server User (long)
Administrative username.
[4] Server Password (string) 
Administrative password.
[5] Service Type (string)
The type of the service to backup.
[6] Services (Multiple Value)
One or more services to perform an action on. The tool will autopopulate with a list of services when the first 5 parameters are entered. Service names must be provided in the <ServiceName>.<ServiceType> style.

The script uses the username and the password to connect to the server with a generatetoken action. After accessing to the server, all services are listed. When the user selects the services to migrate and fills all the parameters the process starts.
A copy of the selected service's sources is made, this copy is placed in the X device. 

