import sys, os, arcpy
import urllib, json, httplib
import shutil
import errno
import string
import datetime, time
import socket
import getpass
import zipfile

def gentoken(server, port, adminUser, adminPass, expiration=300):
    
    #Re-usable function to get a token required for Admin changes
    query_dict = {'username':adminUser,'password':adminPass,'client':'requestip'}
    
    query_string = urllib.urlencode(query_dict)
    
    url = "http://{}:{}/arcgis/admin/generateToken".format(server, port)
    
    token = json.loads(urllib.urlopen(url + "?f=json", query_string).read())
        
    if 'token' not in token:
        arcpy.AddError(token['messages'])
        quit()
    else:
        return token['token']

def formatDate():
    return str(time.strftime('%Y-%m-%d %H:%M:%S'))

def makeAGSconnection(server, port, adminUser, adminPass, workFolder):
    
    ''' Function to create an ArcGIS Server connection file using the arcpy.Mapping function "CreateGISServerConnectionFile"    
    '''
    millis = int(round(time.time() * 1000))
    connectionType = 'ADMINISTER_GIS_SERVICES'
    connectionName = 'ServerConnection' + str(millis)
    serverURL = 'http://' + server + ':' + port + '/arcgis/admin'
    serverType = 'ARCGIS_SERVER'
    saveUserName = 'SAVE_USERNAME'
        
    outputAGS = os.path.join(workFolder, connectionName + ".ags")
    try:
        arcpy.mapping.CreateGISServerConnectionFile(connectionType, workFolder, connectionName, serverURL, serverType, True, '', adminUser, adminPass, saveUserName)
        return outputAGS
    except:
        arcpy.AddError("Could not create AGS connection file for: '" + server + ":" + port + "'")
        sys.exit()
        

# A function that will post HTTP POST request to the server
def postToServer(server, port, url, params):

    httpConn = httplib.HTTPConnection(server, port)
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

    # URL encode the resoure URL
    url = urllib.quote(url.encode('utf-8'))
    
    # Build the connection to add the roles to the server
    httpConn.request("POST", url, params, headers)

    response = httpConn.getresponse()
    data = response.read()
    httpConn.close()
    
    return (response, data)


def numberOfServices(server, port, adminUser, adminPass, serviceType):
    
    #Count all the services of "MapServer" type in a server
    number = 0
    token = gentoken(server, port, adminUser, adminPass)    
    services = []    
    baseUrl = "http://{}:{}/arcgis/admin/services".format(server, port)
    catalog = json.load(urllib.urlopen(baseUrl + "/" + "?f=json&token=" + token))
    services = catalog['services']
    
    for service in services:
        if service['type'] == serviceType:
            number = number + 1
            
    folders = catalog['folders']
    
    for folderName in folders:
        catalog = json.load(urllib.urlopen(baseUrl + "/" + folderName + "?f=json&token=" + token))
        services = catalog['services']
        for service in services:
            if service['type'] == serviceType:
                number = number + 1

    return number


# A function that checks that the input JSON object is not an error object.
def assertJsonSuccess(data):
    
    obj = json.loads(data)
    if 'status' in obj and obj['status'] == "error":
        arcpy.AddMessage("     Error: JSON object returns an error. " + str(obj))
        return False
    else:
        return True


def copy(src, dest):
    
    #Check if folder exists, if exists delete
    if os.path.exists(dest): shutil.rmtree(dest)
    
    #Copy folder
    try:
        shutil.copytree(src, dest)
        return True
    except OSError as e:
        # If the error was caused because the source wasn't a directory
        if e.errno == errno.ENOTDIR:
            shutil.copy(src, dst)
            return True
        elif e.errno == errno.EEXIST:
            arcpy.AddMessage('     The folder already exists.')
            return False
        else:
            arcpy.AddMessage('     Directory not copied. Error: %s' % e)
            return False
    except:
         arcpy.AddMessage('     The source can not be copied because the path is extremely long.')
         return False
        

def createZipFile(folder_path, output_path):
    """Zip the contents of an entire folder (with that folder included
    in the archive). Empty subfolders will be included in the archive
    as well.
    """

    parent_folder = os.path.dirname(folder_path)
    # Retrieve the paths of the folder contents.
    contents = os.walk(folder_path)
    try:
        zip_file = zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED)
        for root, folders, files in contents:
            # Include all subfolders, including empty ones.
            for folder_name in folders:
                absolute_path = os.path.join(root, folder_name)
                relative_path = absolute_path.replace(parent_folder + '\\','')
                zip_file.write(absolute_path, relative_path)
                
            for file_name in files:
                absolute_path = os.path.join(root, file_name)
                relative_path = absolute_path.replace(parent_folder + '\\','')
                zip_file.write(absolute_path, relative_path)


        zip_file.close()
        return True
    
    except IOError, message:
        zip_file.close()
        
        os.remove(output_path)
        return False
    except OSError, message:
        zip_file.close()
        
        os.remove(output_path)
        return False
    except zipfile.BadZipfile, message:
        zip_file.close()
        
        os.remove(output_path)
        return False
    
    except:
        zip_file.close()
        
        arcpy.AddMessage('     The source can not be copied because the path is extremely long.')
        os.remove(output_path)
        return False
        

def backupMapServices(serverName, serverPort, adminUser, adminPass, serviceList, serviceType, workFolder, token=None):
    serviceSuccesNumber = 0
    serviceFailureNumber = 0
    sources = ""

    workFolder = workFolder + "\\"
    
    content1 = "\n *************************************************************************** \n           Making BACKUP \n           " + formatDate() + "\n *************************************************************************** "
  
    # Getting services from tool validation creates a semicolon delimited list that needs to be broken up
    services = serviceList.split(';')

    #modify the services(s)    
    for service in services:                                            
        service = urllib.quote(service.encode('utf8'))
        serviceURL = "/arcgis/admin/services/" + service

        # Get and set the token
        token = gentoken(serverName, serverPort, adminUser, adminPass)

        # This request only needs the token and the response formatting parameter 
        params = urllib.urlencode({'token': token, 'f': 'json'})
        response, data = postToServer(serverName, str(serverPort), serviceURL, params)
        
        if (response.status != 200):
            arcpy.AddMessage("\n  ** Could not read service '" + str(service) + "' information.")
        else:
            # Check that data returned is not an error object
            if not assertJsonSuccess(data): arcpy.AddMessage("\n  ** Error when reading service '" + str(service) + "' information. " + str(data))
            else:
                arcpy.AddMessage("\n  ** Service '" + str(service) + "' information read successfully.")

                # Deserialize response into Python object
                propInitialService = json.loads(data)

                pathInitial = propInitialService["properties"]["filePath"]
                
                pathInitial = pathInitial.replace(':', '', 1)
                msdPath = pathInitial.replace('X', os.path.join(r'\\' + serverName, 'x'), 1)
                
                #msdPath = string.replace(pathInitial, 'X:', os.path.join(r'\\' + serverName, 'x'))

                folderName = os.path.split(service)[0]
                serviceName = os.path.split(service)[1]
                serviceName2 = serviceName
                pos3 = serviceName2.find(".MapServer")
                simpleServiceName = serviceName2[:pos3]


                if  folderName != 'root' or folderName != '':                           
                    finalServiceName = folderName + "//" + simpleServiceName + ".MapServer"
                else:
                    finalServiceName = serviceName                 

                #The path of the folder that contains the service info
                if folderName != "":
                    if not os.path.exists(workFolder + folderName):
                        os.makedirs(workFolder + folderName)
                    serviceName = folderName + "\\" + serviceName

                pos = msdPath.find(serviceName) + len(serviceName) 
                inputFolderPath = msdPath[:pos]       

                #Copy service data
                continuePublish1 = copy(inputFolderPath, workFolder + serviceName)
                continuePublish2 = createZipFile(inputFolderPath, workFolder + "\\" + serviceName + ".zip")

                if continuePublish1 == True and continuePublish2 == True:
                    serviceSuccesNumber = serviceSuccesNumber + 1
                    arcpy.AddMessage("  ** Backup done succesfully.")
                else:
                    serviceFailureNumber = serviceFailureNumber + 1
                    arcpy.AddMessage("  ** Error when backing up.")

                    try:
                        shutil.rmtree(workFolder + serviceName)
                    except:
                        pass

    number = numberOfServices(serverName, serverPort, adminUser, adminPass, serviceType)

    workFolder = workFolder.replace(':', '', 1)
    backup_path = workFolder.replace('X', os.path.join(r'\\' + socket.gethostname(), 'x'), 1)
    #backup_path = string.replace(workFolder, 'X:', os.path.join(r'\\' + socket.gethostname(), 'x'))
    
    arcpy.AddMessage("\n***************************************************************************  ")
    arcpy.AddMessage(" - Number of services in '" + serverName + "': " + str(number))
    arcpy.AddMessage(" - Number of services selected in '" + serverName + "': " + str(len(services)))
    arcpy.AddMessage(" - Number of services backed up successfully: " + str(serviceSuccesNumber))
    arcpy.AddMessage(" - Number of services not backed up: " + str(serviceFailureNumber))
    
    arcpy.AddMessage("\n - The service backup is placed in: " + backup_path)
        
    arcpy.AddMessage("***************************************************************************  ")
   

if __name__ == "__main__":

    # Gather inputs    
    serverName = arcpy.GetParameterAsText(0)
    serverPort = arcpy.GetParameterAsText(1)
    adminUser = arcpy.GetParameterAsText(2)
    adminPass = arcpy.GetParameterAsText(3)
    serviceType = arcpy.GetParameterAsText(4) 
    serviceList = arcpy.GetParameterAsText(5)
    backupPath = arcpy.GetParameterAsText(6)

    #sysTemp = tempfile.gettempdir()    
    if not os.path.exists(backupPath):
        os.makedirs(backupPath)
      
    now = datetime.datetime.now()
    workFolder = os.path.join(backupPath, str(now.year) + str(now.month) + str(now.day) + '_' + str(now.hour) + str(now.minute) + str(now.second) + '_' + serverName)
   
    if not os.path.exists(workFolder):
        os.makedirs(workFolder)
    
    if serviceType == "MapServer":
        backupMapServices(serverName, serverPort, adminUser, adminPass, serviceList, serviceType, workFolder)

