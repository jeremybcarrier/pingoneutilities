# PingOne Import Tool - Configurator
# Last Update: June 26, 2025
# Authors: Matt Pollicove, Jeremy Carrier

import os
import re
import requests
import base64
import csv
import pwinput
import configparser

def printWelcome(version):
    # *********
    # Prints a welcome message and instructions for the configuration tool.
    # *********
    print(f'')
    print(f'')
    print(f'********************************************')
    print(f'PingOne User Import Utility - version {version}')
    print(f'Configuration Tool')
    print(f'********************************************')
    print(f'')
    print(f'This tool will walk you through the configuration of the User Import Tool.  You will need the following:')
    print(f'1) Your PingOne Environment ID')
    print(f'2) Your PingOne Geography')
    print(f'3) A PingOne Worker Client ID, Client Secret, and Authenticaiton Type (basic vs. post)')
    print(f'4) Your user file')
    print(f'5) Knowledge of user attributes in P1 for mapping')
    print(f'')

def getConfigFileName(workingDirectory):
    # *********
    # Prints the path where the configuration file will be written.
    # *********
    print(f'Writing configuration file to: {workingDirectory}/P1ImportUser.cfg')
    print(f'')

def getP1Environment(p1Environment, guidFormat):
    # *********
    # Prompts the user for the PingOne Environment ID and validates its format.
    # *********
    getEnvironmentId = input(f'What is your PingOne Environment ID? (format: {p1Environment}):')
    if re.match(guidFormat,getEnvironmentId):
        print(f'')
        return getEnvironmentId
    else:
        print(f'')
        print(f'*****************************************************************')
        print(f'Error: The format of the environment ID is invalid, please retry.')
        print(f'*****************************************************************')
        print(f'')
        getEnvironmentId = getP1Environment()

def getP1Geo():
    # *********
    # Prompts the user for the PingOne Geography and validates its format.
    # *********
    getGeo = input(f'What is your PingOne Geography? (.com, .ca, .asia, .au, .eu, etc.): [.com] ')
    if not getGeo:
        getGeo = ".com"  # Default to .com if no input is provided
        return getGeo.lower()
    else:
        if re.match(r"^\.[a-zA-Z]{1,4}$",getGeo):
            print(f'')
            return getGeo.lower()
        else:
            # Geo format is invalid, retry
            print(f'')
            print(f'*****************************')
            print(f"Invalid format, please retry.")
            print(f'*****************************')
            print(f'')
            getGeo = getP1Geo()

def getP1ClientId(p1ClientId, guidFormat):
    # *********
    # Prompts the user for the PingOne Client ID and validates its format.
    # *********
    getClientId = input(f'What is your PingOne Client ID? (format: {p1ClientId}):')
    if re.match(guidFormat,getClientId):
        print(f'')
        return getClientId.lower()
    else:
        # Client ID format is invalid, retry
        print(f'')
        print(f'************************************************************')
        print(f'Error: The format of the client ID is invalid, please retry.')
        print(f'************************************************************')
        print(f'')
        getClientId = getP1ClientId(p1ClientId, guidFormat)

def getP1ClientSecret():
    # *********
    #Prompts the user for the PingOne Client Secret securely.
    # *********
    getClientSecret = pwinput.pwinput(prompt='What is your PingOne Client Secret? :', mask='*')
    print(f'')
    return getClientSecret

def convertCreds(p1ClientId, p1ClientSecret):
    # *********
    # Converts the client ID and secret to a base64-encoded string for HTTP Basic Auth.
    # *********
    credString = p1ClientId + ":" + p1ClientSecret
    credBytes = credString.encode("ascii")
    b64CredBytes = base64.b64encode(credBytes)
    b64CredString = b64CredBytes.decode("ascii") 
    return b64CredString

def performClientTestBasic(p1ClientId, p1ClientSecret, p1Geography, p1Environment):
    # *********
    # Attempts to authenticate with PingOne using the provided credentials using BASIC auth.
    # *********
    requestHeaders = ""

    print(f'')
    print(f'Checking client credentials with PingOne - attempting BASIC auth.')
    print(f'')

    # Call P1 token endpoint to get an access token with basic encoding
    p1CredsB64 = convertCreds(p1ClientId, p1ClientSecret)
    requestHeaders = {}
    requestHeaders['Authorization'] = 'Basic ' + p1CredsB64
    requestHeaders['Content-Type'] = 'application/x-www-form-urlencoded'
    requestBody = {'grant_type':'client_credentials'}


    try:
        hostCheckResult = requests.post(f"https://auth.pingone{p1Geography}/{p1Environment}/as/token",headers=requestHeaders,data=requestBody)
        if hostCheckResult.status_code == 200:
            print(f"Client connection validated with BASIC auth.")
            print(f'')
            return True, hostCheckResult.json()['access_token']
        else:
            print(f'')
            print(f"****************************************************")
            print(f"Failed to connect to PingOne client with BASIC auth.")
            print(f"****************************************************")
            print(f'')
            return False,""
    except requests.exceptions.RequestException:
        print(f'')
        print(f"****************************************************")
        print(f"Failed to connect to PingOne client with BASIC auth.")
        print(f"****************************************************")
        print(f'')
        return False,""

def performClientTestPost(p1ClientId, p1ClientSecret, p1Geography, p1Environment):
    # *********
    # Attempts to authenticate with PingOne using the provided credentials using POST auth.
    # *********
    requestHeaders = ""

    print(f'')
    print(f'Checking client credentials with PingOne - attempting POST auth.')
    print(f'')

    # Call p1 token endpoint to get an access token with post encoding
    requestHeaders = {}
    requestHeaders['Content-Type'] = 'application/x-www-form-urlencoded'
    requestBody = {}
    requestBody['client_id'] = p1ClientId
    requestBody['client_secret'] = p1ClientSecret
    requestBody['grant_type'] = 'client_credentials'

    try:
        hostCheckResult = requests.post(f"https://auth.pingone{p1Geography}/{p1Environment}/as/token",headers=requestHeaders,data=requestBody)
        if hostCheckResult.status_code == 200:
            print(f"Client connection validated with POST auth.")
            print(f'')
            return True, hostCheckResult.json()['access_token']
        else:
            print(f'')
            print(f'***************************************************')
            print(f"Failed to connect to PingOne client with POST auth.")
            print(f'***************************************************')
            print(f'')
            return False,""
    except requests.exceptions.RequestException:
        print(f'')
        print(f'***************************************************')
        print(f"Failed to connect to PingOne client with POST auth.")
        print(f'***************************************************')
        print(f'')  
        return False, ""

def getP1ClientType(p1ClientId, p1ClientSecret, p1Geography, p1Environment):
    # *********
    # Tries to determine client type (basic or post)
    # *********

    # Try basic
    tryBasic, p1At = performClientTestBasic(p1ClientId, p1ClientSecret, p1Geography, p1Environment)

    if tryBasic == True:
        return "basic", p1At
    else:
        # Try post
        tryPost, p1At = performClientTestPost(p1ClientId, p1ClientSecret, p1Geography, p1Environment)
        if tryPost == True:
            return "post", p1At
        else:
            print(f'')
            print(f'**************************************************************************************************************************************')
            print(f'Error: Failed to connect to client with both BASIC and POST.  Please re-enter client details and ensure your worker client is enabled.')
            print(f'**************************************************************************************************************************************')
            return "failed",""

def getTokenRefreshDuration():
    # *********
    # Prompts the user for the token refresh duration (in minutes) and validates the input.
    # *********
    getRefreshDuration = input(f'How often do you want to refresh the worker access token, in minutes (59 minutes max)?: [30]')
    if not getRefreshDuration:
        getRefreshDuration = "30"  # Default to 30 minutes if no input is provided
        return getRefreshDuration
    else:
        if re.match(r"^[0-9]{1,2}$", getRefreshDuration):
            if((int(getRefreshDuration) > 0) and (int(getRefreshDuration) < 60)):
                print(f'')
                return getRefreshDuration
            else:
                print(f'')
                print(f'*****************************************************************')
                print(f"Invalid duration - must be numeric, greater than 0, less than 60.")
                print(f'*****************************************************************')
                print(f'')
                getRefreshDuration = getTokenRefreshDuration()
        else:
            print(f'')
            print(f"*****************************************************************")
            print(f"Invalid duration - must be numeric, greater than 0, less than 60.")
            print(f'*****************************************************************')
            print(f'')
            getRefreshDuration = getTokenRefreshDuration()

def getCsvFileName():
    # *********
    # Prompts the user for the absolute path to the CSV file and checks if it exists.
    # *********

    foundCsvFile = False
    currentDirectory = os.getcwd()
    firstFile = ""

    print(f'Retrieving the list of CSV files in the current working directory.')
    print(f'')

    # get all files/diretories in the current working directory
    allFiles = os.listdir(currentDirectory)
    for file in allFiles:
        if file.endswith(".csv"):
            if foundCsvFile == False:
                foundCsvFile = True
                firstFile = currentDirectory + "/" + file
                print(f'The following CSV files were found in the current working directory:')
            print(f' - {currentDirectory}/{file}')

    if foundCsvFile == False:
        print(f'')
        print(f'*******************************************************************************')
        print(f'No CSV files were found in the current working directory ({currentDirectory}).')
        print(f'Please ensure you have a CSV file in this directory before proceeding.')
        print(f'*******************************************************************************')
        print(f'')
        tryAgain = input(f'Press Enter to try again.')
        return getCsvFileName()
    else:
        print(f'')

    getFileName = input(f'What is the absolute path of your CSV file?: [{firstFile}]')
    if not getFileName:
        getFileName = firstFile
        return getFileName
    else:
        if os.path.exists(getFileName):
            print(f'')
            return getFileName
        else:
            print(f'')
            print(f"**********************************************************")
            print(f"File could not be found ({getFileName}), please try again.")
            print(f"**********************************************************")
            print(f'')
            getFileName = getCsvFileName()

def getSubattributes(p1AttributeNames, p1Attribute):
    # *********
    # Appends subattribute names for complex PingOne attributes to the attribute list.
    # *********
    print(f"Reading subattributes for attribute {p1Attribute['name']}.")
    for subattribute in p1Attribute['subAttributes']:
        p1AttributeNames.append(p1Attribute['name'] + "." + subattribute['name'])
    print(f'')

def getP1UserAttributes(p1At, p1Environment, p1Geography):
    # *********
    # Retrieves the list of user attributes from the PingOne environment.
    # Returns a list of attribute names.
    # *********
    requestSchemaHeaders = {}
    requestSchemaHeaders['Authorization'] = "Bearer " + p1At
    requestAttributeHeaders = {}
    requestAttributeHeaders['Authorization'] = "Bearer " + p1At
    p1AttributeNames = []

    #Get the Schema for the PingOne environment
    try:
        print(f"Reading PingOne Schema from environment {p1Environment}.")
        print(f'')
        getSchema = requests.get(f"https://api.pingone{p1Geography}/v1/environments/{p1Environment}/schemas",headers=requestSchemaHeaders)
        if getSchema.status_code == 200:
            schemaId = getSchema.json()['_embedded']['schemas'][0]['id']
        else:
            print(f'')
            print(f'*******************************************************************************************************************')
            print(f"Failed to read the schema of your PingOne environment.  Please ensure your worker has appropriate rights.  Exiting.")
            print(f'*******************************************************************************************************************')
            print(f'')
            quit()
            
    except:
        print(f'')
        print(f'*******************************************************************************************************************')
        print(f"Failed to read the schema of your PingOne environment.  Please ensure your worker has appropriate rights.  Exiting.")
        print(f'*******************************************************************************************************************')
        print(f'')
        quit()

    #Get the Attributes for the PingOne environment
    try:
        print(f"Reading user attributes from environment {p1Environment}.")
        print(f'')
        getAttributes = requests.get(f"https://api.pingone{p1Geography}/v1/environments/{p1Environment}/schemas/{schemaId}/attributes",headers=requestAttributeHeaders)
        if getAttributes.status_code == 200:
            for p1Attribute in getAttributes.json()['_embedded']['attributes']:
                if(p1Attribute['type'] == "COMPLEX"):
                    getSubattributes(p1AttributeNames, p1Attribute)
                else:
                    p1AttributeNames.append(p1Attribute['name'])

            p1AttributeNames.append("password")
            p1AttributeNames.append("mfaEmail1")
            p1AttributeNames.append("mfaEmail2")
            p1AttributeNames.append("mfaSmsVoice1")
            p1AttributeNames.append("mfaSmsVoice2")

            return p1AttributeNames
        else:
            print(f'') 
            print(f'*********************************************************************************************************************')
            print(f"Failed to read the attributes of your PingOne environment.  Please ensure your worker has appropriate rights.  Exiting.")
            print(f'*********************************************************************************************************************')
            print(f'')
            quit()
    except:
        print(f'')
        print(f'**********************************************************************************************************************')
        print("Failed to read the attributes of your PingOne environment.  Please ensure your worker has appropriate rights.  Exiting.")
        print(f'**********************************************************************************************************************')
        print(f'')
        quit()


def validateCsvHeaders(userFile):
    # *********
    #  Reads and returns the headers from the provided CSV file.
    # Returns a tuple ("true", [headers]) if successful.
    # *********
    readCsvHeaders = []

    try:
        with open(userFile, 'r', newline='', encoding='utf-8-sig') as csvFile:
            csvFileReader = csv.reader(csvFile)
            csvFileHeaders = next(csvFileReader)
    except Exception as csvException:
        print(f'')
        print(f"*********************************************************************************************************")
        print(f"There was an issue reading your CSV file headers: ", csvException)
        print(f"Please correct this issue and retry.  Exiting.")
        print(f"*********************************************************************************************************")
        print(f'')
        quit()

    for header in csvFileHeaders:
        readCsvHeaders.append(header.strip())
    
    return "true", readCsvHeaders

def printMappingIntro():
    # *********
    # Prints an introduction to the CSV header mapping validation step.
    # *********

    print(f"The configuration tool will now validate the CSV headers against the available attributes in the provided PingOne environment.")
    print(f'')

def checkHeadersVsAttributes(csvHeaders, p1Attributes):
    # *********
    # Checks if each CSV header matches a known PingOne attribute.
    # Returns "true" if all headers match, otherwise "false".
    # *********
    print(csvHeaders)
    for header in csvHeaders:
        print(header)
        currentAttributeMappingMatch = "false"
        for attribute in p1Attributes:
            if(attribute == header):
                currentAttributeMappingMatch = "true"
                print(f"CSV Header ({header}) matched with PingOne attribute ({attribute}).")
        if currentAttributeMappingMatch == "false":
            print(f'')
            print(f'******************************************************************************************************************************************************')
            print(f"Unable to map CSV Header ({header}) with any known PingOne attribute.  Please check your CSV file and ensure the headers match the PingOne attributes.")
            print(f'If you are using a complex attribute, please ensure the header is in the format of <attribute>.<subattribute> (e.g., "name.given").')
            print(f'Exiting.')
            print(f'******************************************************************************************************************************************************')
            print(f'')
            quit()
    print(f'')

def getForcedPasswordChange():
    # *********
    # Prompts the user to specify whether or not imported accounts should be required to change password on first login.
    # *********
    getPasswordChange = input(f'After import, should users be forced to reset their password at first login? (true/false): [false] ')
    if not getPasswordChange:
        getPasswordChange = "false"  # Default to false if no input is provided
        return getPasswordChange.lower()
    else:
        if re.match(r"^(true|false)$", getPasswordChange.lower()):
            print(f'')
            return getPasswordChange.lower()
        else:
            # Invalid input, retry
            print(f'')
            print(f'**********************************************')
            print(f'Error: Please response either (true) or (false).')
            print(f'**********************************************')
            print(f'')
            getPasswordChange = getForcedPasswordChange()

def getP1Populations(p1At, p1Environment, p1Geography):
    # *********
    # Retrieves the list of populations from the PingOne environment.
    # Returns a list of population IDs.
    # *********
    requestPopHeaders = {}
    requestPopHeaders['Authorization'] = "Bearer " + p1At
    firstPopulation = ""

    try:
        print(f"Reading PingOne populations from environment {p1Environment}.")
        print(f'')
        print(f'The following populations were found in the environment:')
        getPopulations = requests.get(f"https://api.pingone{p1Geography}/v1/environments/{p1Environment}/populations",headers=requestPopHeaders)
        if getPopulations.status_code == 200:
            for p1Population in getPopulations.json()['_embedded']['populations']:
                print(f' - ({p1Population["name"]}) {p1Population["id"]} ')
                if firstPopulation == "":
                    firstPopulation = p1Population['id']
            print(f'')
            return firstPopulation
        else:
            print(f'')
            print(f'*******************************************************************************************************************')
            print(f"Failed to read the populations of your PingOne environment.  Please ensure your worker has appropriate rights.  Exiting.")
            print(f'*******************************************************************************************************************')
            print(f'')
            quit()
    except:
        print(f'')
        print(f'*******************************************************************************************************************')
        print("Failed to read the populations of your PingOne environment.  Please ensure your worker has appropriate rights.  Exiting.")
        print(f'*******************************************************************************************************************')
        print(f'')
        quit()

def getDefaultPopulation(p1At, p1Environment, p1Geography, defaultPopulation, guidFormat):
    # *********
    # Prompts the user to specify the default population for the imported users.
    # *********
    defaultP1Population = getP1Populations(p1At, p1Environment, p1Geography)

    getDefaultPopulation = input(f'For users where a PingOne population is not specified, what deafault population id should be used?: [{defaultP1Population}] ')
    if not getDefaultPopulation:
        getDefaultPopulation = defaultP1Population
        return getDefaultPopulation.lower()
    else:
        if re.match(guidFormat,getDefaultPopulation):
            print(f'')
            return getDefaultPopulation.lower()
        else:
            # Default population format is invalid, retry
            print(f'')
            print(f'*************************************************************')
            print(f'Error: The format of the population is invalid, please retry.')
            print(f'*************************************************************')
            print(f'')
            getDefaultPopulation = getDefaultPopulation()

def writeConfigFile(version, workingDirectory, p1Environment, p1Geography, p1ClientId, p1ClientSecret, p1ClientType, tokenRefresh, userFile, forcedPasswordChange, defaultPopulation):
    # *********
    # Writes the configuration details to a config file in the working directory.
    # *********
    configFile = configparser.ConfigParser()

    configFile['General']  = {'version': version, 'workingDirectory':workingDirectory}
    configFile['P1Config'] = {'p1Environment':p1Environment, 'p1Geography':p1Geography, 'p1ClientId':p1ClientId, 'p1ClientSecret':p1ClientSecret, 'p1ClientType':p1ClientType, 'tokenRefresh':tokenRefresh, 'forcedPasswordChange':forcedPasswordChange, 'defaultPopulation':defaultPopulation}
    configFile['CSV'] = {'CSV Path':userFile}
    with open(workingDirectory + "/P1ImportUser.cfg", "w") as csvFile:
        configFile.write(csvFile)

def closeConfigurator(workingDirectory):
    # *********
    # Prints a message indicating that configuration is complete and shows the config file path.
    # *********
    print("All configuration complete - the configuration file has been written to :")
    print(workingDirectory + '/P1ImportUser.cfg')

def main():
    # *********
    # Main function to run the configuration workflow for the PingOne User Import Tool.
    # *********
    version = 0.2
    workingDirectory = os.getcwd()
    guidFormat = r"^[a-fA-f0-9]{8}-[a-fA-f0-9]{4}-[a-fA-f0-9]{4}-[a-fA-f0-9]{4}-[a-fA-f0-9]{12}$"
    p1Environment = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    p1Geography = ".com"
    p1ClientId = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    p1ClientSecret = "?"
    p1CredsB64 = ""
    p1ClientType = "failed"
    p1ClientTest = "false"
    tokenRefresh = 30
    userFile = "users.csv"
    validCsvHeaders = "false"
    p1Attributes = []
    csvHeaders = []
    forcedPasswordChange = "false"
    defaultPopulation = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    printWelcome(version)
    getConfigFileName(workingDirectory)
    while (p1ClientTest == "false") and \
          (p1ClientType == "failed"):
        p1Environment = getP1Environment(p1Environment, guidFormat)
        p1Geography = getP1Geo()
        p1ClientId = getP1ClientId(p1ClientId, guidFormat)
        p1ClientSecret = getP1ClientSecret()
        p1ClientType, p1AccessToken = getP1ClientType(p1ClientId, p1ClientSecret, p1Geography, p1Environment)
        if (p1ClientType != "failed"):
            tokenRefresh = getTokenRefreshDuration()
    userFile = getCsvFileName()
    p1Attributes = getP1UserAttributes(p1AccessToken, p1Environment, p1Geography)
    while (validCsvHeaders == "false"):
        validCsvHeaders, csvHeaders = validateCsvHeaders(userFile)
    printMappingIntro()
    checkHeadersVsAttributes(csvHeaders, p1Attributes)
    forcedPasswordChange = getForcedPasswordChange()
    defaultPopulation = getDefaultPopulation(p1AccessToken, p1Environment, p1Geography, defaultPopulation, guidFormat)
    writeConfigFile(version, workingDirectory, p1Environment, p1Geography, p1ClientId, p1ClientSecret, p1ClientType, tokenRefresh, userFile, forcedPasswordChange, defaultPopulation)
    closeConfigurator(workingDirectory)

main()