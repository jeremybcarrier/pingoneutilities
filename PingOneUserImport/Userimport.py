# PingOne Import Tool
# Last Update: June 17, 2025
# Authors: Matt Pollicove, Jeremy Carrier

# Open config file*
# check working directory*
# check version*
# test P1 client*
# check CSV file*
# read headers of csv and create array of headers*
# get access token from P1*
# read 100 lines of csv*
# import 100 users*
# check to make sure we haven't crossed 100tps, thread as needed
# log everything

import configparser
import requests
import os
import base64
import csv
from ratelimit import limits, sleep_and_retry
import logging
import threading
import time

logger = logging.basicConfig(filename='P1ImportUser.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def printWelcome(version):
    #######
    # Print the welcome message
    #######

    startTime = int(time.time() * 1000) 
    
    print(f'')
    print(f'********************************************')
    print(f'PingOne User Import Utility - version {version}')
    print(f'********************************************')
    print(f'')
    print(f'Actions will be written to the log file P1ImportUser.log')
    print(f'')
    logging.info(f"PingOne User Import Utility - version {version}")
    logging.info(f"Starting import tool: {startTime}")

    return startTime

def readConfigurationFile(workingDirectory, configVersion, configWorkingDirectory, p1Environment, p1Geography, p1ClientId, p1ClientSecret, p1ClientType, tokenRefresh, p1DefaultPopulation, p1PasswordReset, csvPath):
    #######
    # Read the configuration file
    #######


    print(f'Reading configuration file: {workingDirectory}/P1ImportUser.cfg')
    print(f'')
    logging.info(f"Reading config file: {workingDirectory}/P1ImportUser.cfg")
    
    if(os.path.isfile('P1ImportUser.cfg')):
        try:
            configFile = configparser.ConfigParser()
            configFile.read('P1ImportUser.cfg')
        except Exception as e:
            print("Error reading configuration file: ", e)
            logging.error(f"Error reading configuration file: {e}")
            quit()

        if "General" in configFile.sections():
            if("version" in configFile["General"]) and \
              ("workingdirectory" in configFile["General"]):
                configVersion = configFile["General"]["version"]
                configWorkingDirectory = configFile["General"]["workingdirectory"]
            else:
                print("Error: Missing required fields in General section of configuration file - please re-run configuration utility.")
                logging.error(f"Missing required fields in General section of configuration file - please re-run configuration utility.")
                quit()
        else:
            print("Error: Missing General section in configuration file - please re-run configuration utility.")
            logging.error(f"Missing General section in configuration file - please re-run configuration utility.")
            quit()

        if "P1Config" in configFile.sections():
            if("p1environment" in configFile["P1Config"]) and \
              ("p1geography" in configFile["P1Config"]) and \
              ("p1clientid" in configFile["P1Config"]) and \
              ("p1clientsecret" in configFile["P1Config"]) and \
              ("p1clienttype" in configFile["P1Config"]) and \
              ("tokenrefresh" in configFile["P1Config"]):
                p1Environment = configFile["P1Config"]["p1environment"]
                p1Geography = configFile["P1Config"]["p1geography"]
                p1ClientId = configFile["P1Config"]["p1clientid"]
                p1ClientSecret = configFile["P1Config"]["p1clientsecret"]
                p1ClientType = configFile["P1Config"]["p1clienttype"]
                p1DefaultPopulation = configFile["P1Config"]["defaultpopulation"]
                p1PasswordReset = configFile["P1Config"]["forcedpasswordchange"]
                tokenRefresh = int(configFile["P1Config"]["tokenrefresh"])
            else:
                print("Error: Missing required fields in P1Config section of configuration file - please re-run configuration utility.")
                logging.error(f"Missing required fields in P1Config section of configuration file - please re-run configuration utility.")
                quit()
        else:
            print("Error: Missing P1Config section in configuration file - please re-run configuration utility.")
            logging.error(f"Missing P1Config section in configuration file - please re-run configuration utility.")
            quit()

        if "CSV" in configFile.sections():
            if("csv path" in configFile["CSV"]):
                csvPath = configFile["CSV"]["csv path"]
            else:
                print("Error: Missing required fields in CSV section of configuration file - please re-run configuration utility.")
                logging.error(f"Missing required fields in CSV section of configuration file - please re-run configuration utility.")
                quit()
        else:
            print("Error: Missing CSV section in configuration file - please re-run configuration utility.")
            logging.error(f"Missing CSV section in configuration file - please re-run configuration utility.")
            quit()
    else:
        print("Error: Configuration file not found - please run configuration utility to create the configuration file.")
        logging.error(f"Configuration file not found - please run configuration utility to create the configuration file.")
        quit()

    print(f'Configuration file read successfully.')
    logging.info(f"Configuration file read successfully.")
    print(f'')
    return configVersion, configWorkingDirectory, p1Environment, p1Geography, p1ClientId, p1ClientSecret, p1ClientType, tokenRefresh, p1DefaultPopulation, p1PasswordReset, csvPath

def checkWorkingDirectory(workingDirectory, configWorkingDirectory):
    #######
    # Check the working directory
    #######

    if(workingDirectory != configWorkingDirectory):
        print(f'Error: Working directory {workingDirectory} does not match configured working directory {configWorkingDirectory}.')
        print(f'Please change to the correct working directory and re-run the utility.')
        logging.error(f"Working directory {workingDirectory} does not match configured working directory {configWorkingDirectory}.")
        quit()
    else:
        print(f'Working directory validated - matches configuration file: {workingDirectory}')
        logging.info(f"Working directory validated - matches configuration file: {workingDirectory}")
        print(f'')

def checkVersion(configVersion, version):
    #######
    # Check the version
    #######

    if(configVersion != version):
        print(f'Error: Configuration file version {configVersion} does not match utility version {version}.')
        print(f'Please re-run the configuration utility to update the configuration file.')
        logging.error(f"Configuration file version {configVersion} does not match utility version {version}.")
        quit()
    else:
        print(f'Configuration file version validated - matches configuration version: {version}')
        logging.info(f"Configuration file version validated - matches configuration version: {version}")
        print(f'')

def convertCreds(p1ClientId, p1ClientSecret):
    # *********
    # Converts the client ID and secret to a base64-encoded string for HTTP Basic Auth.
    # *********
    credString = p1ClientId + ":" + p1ClientSecret
    credBytes = credString.encode("ascii")
    b64CredBytes = base64.b64encode(credBytes)
    b64CredString = b64CredBytes.decode("ascii") 
    return b64CredString

def performClientTest(p1ClientId, p1ClientSecret, p1Geography, p1Environment, p1ClientType):
    # *********
    # Attempts to authenticate with PingOne using the provided credentials and client type.
    # *********
    requestHeaders = ""

    print(f'')
    print(f'Checking client credentials with PingOne.')
    logging.info(f"Checking client credentials with PingOne.")
    print(f'')

    # Call P1 token endpoint to get an access token with basic encoding
    if p1ClientType == "basic":
        p1CredsB64 = convertCreds(p1ClientId, p1ClientSecret)
        requestHeaders = {}
        requestHeaders['Authorization'] = 'Basic ' + p1CredsB64
        requestHeaders['Content-Type'] = 'application/x-www-form-urlencoded'
        requestBody = {'grant_type':'client_credentials'}


        try:
            hostCheckResult = requests.post(f"https://auth.pingone{p1Geography}/{p1Environment}/as/token",headers=requestHeaders,data=requestBody)
            if hostCheckResult.status_code == 200:
                print(f"Client connection validated.")
                logging.info(f"Client connection validated.")
                print(f'')
            else:
                print(f'')
                print(f"****************************************************************************************************************************")
                print(f"Failed to connect to PingOne client with provided parameters.  Please check your worker or re-run the configuration utility.")
                print(f"****************************************************************************************************************************")
                logging.error(f"Failed to connect to PingOne client with provided parameters.  Please check your worker or re-run the configuration utility.")
                print(f'')
        except requests.exceptions.RequestException:
            print(f'')
            print(f"****************************************************************************************************************************")
            print(f"Failed to connect to PingOne client with provided parameters.  Please check your worker or re-run the configuration utility.")
            print(f"****************************************************************************************************************************")
            logging.error(f"Failed to connect to PingOne client with provided parameters.  Please check your worker or re-run the configuration utility.")
            print(f'')

    # Call P1 token endpoint to get an access token with post encoding
    if p1ClientType == "post":
        requestHeaders = {}
        requestHeaders['Content-Type'] = 'application/x-www-form-urlencoded'
        requestBody = {}
        requestBody['client_id'] = p1ClientId
        requestBody['client_secret'] = p1ClientSecret
        requestBody['grant_type'] = 'client_credentials'

        try:
            hostCheckResult = requests.post(f"https://auth.pingone{p1Geography}/{p1Environment}/as/token",headers=requestHeaders,data=requestBody)
            if hostCheckResult.status_code == 200:
                print(f"Client connection validated.")
                logging.info(f"Client connection validated.")
                print(f'')
            else:
                print(f'')
                print(f'****************************************************************************************************************************')
                print(f"Failed to connect to PingOne client with provided parameters.  Please check your worker or re-run the configuration utility.")
                print(f'****************************************************************************************************************************')
                logging.error(f"Failed to connect to PingOne client with provided parameters.  Please check your worker or re-run the configuration utility.")
                print(f'')
        except requests.exceptions.RequestException:
            print(f'')
            print(f'****************************************************************************************************************************')
            print(f"Failed to connect to PingOne client with provided parameters.  Please check your worker or re-run the configuration utility.")
            print(f'****************************************************************************************************************************')
            logging.error(f"Failed to connect to PingOne client with provided parameters.  Please check your worker or re-run the configuration utility.")
            print(f'')  

def ensureCsvExists(csvPath):
    #######
    # Ensure the CSV file exists
    #######

    print(f'Checking for CSV file: {csvPath}')
    logging.info(f"Checking for CSV file: {csvPath}")
    print(f'')

    if(os.path.isfile(csvPath)):
        print(f'CSV file found: {csvPath}')
        logging.info(f"CSV file found: {csvPath}")
        print(f'')
    else:
        print(f'Error: CSV file not found at {csvPath}. Please re-run the configuration utility.')
        logging.error(f"CSV file not found at {csvPath}. Please re-run the configuration utility.")
        quit()

def readCsvHeaders(csvPath):
    #######
    # Read the headers of the CSV file
    #######

    csvHeaders = []

    print(f'Reading CSV file headers from: {csvPath}')
    logging.info(f"Reading CSV file headers from: {csvPath}")
    print(f'')

    try:
        with open(csvPath, 'r', newline='', encoding='utf-8-sig') as csvFile:
            csvFileReader = csv.reader(csvFile)
            headers = next(csvFileReader)
    except Exception as e:
        print(f'Error reading CSV file: {e}')
        logging.error(f"Error reading CSV file: {e}")
        quit()

    for header in headers:
        csvHeaders.append(header.strip())

    return csvHeaders, csvFileReader

def getP1At(p1ClientId, p1ClientSecret, p1Geography, p1Environment, p1ClientType):
    #######
    # Get the access token from PingOne
    #######

    tokenTime = int(time.time() * 1000)

    print(f'Getting access token from PingOne at {tokenTime}.')
    logging.info(f"Getting access token from PingOne at {tokenTime}.")
    print(f'')

    if p1ClientType == "basic":
        p1CredsB64 = convertCreds(p1ClientId, p1ClientSecret)
        requestHeaders = {}
        requestHeaders['Authorization'] = 'Basic ' + p1CredsB64
        requestHeaders['Content-Type'] = 'application/x-www-form-urlencoded'
        requestBody = {}
        requestBody['grant_type'] = 'client_credentials'

    if p1ClientType == "post":
        requestHeaders = {}
        requestHeaders['Content-Type'] = 'application/x-www-form-urlencoded'
        requestBody = {}
        requestBody['client_id'] = p1ClientId
        requestBody['client_secret'] = p1ClientSecret
        requestBody['grant_type'] = 'client_credentials'

    try:
        response = requests.post(f"https://auth.pingone{p1Geography}/{p1Environment}/as/token", headers=requestHeaders, data=requestBody)
        if response.status_code == 200:
            responseJson = response.json()
            return responseJson['access_token'], tokenTime
        else:
            print(f'Error getting access token: {response.status_code} - {response.text}')
            logging.error(f"Error getting access token: {response.status_code} - {response.text}")   
            quit()
    except requests.exceptions.RequestException as e:
        print(f'Error connecting to PingOne: {e}')
        logging.error(f"Error connecting to PingOne: {e}")
        quit()

def readNext100(csvReader):
    #######
    # Read the next 100 rows of the CSV file
    #######

    csvRows = []
    readRows = 0
    notEof = True

    while readRows < 100 and notEof == True:
        try:
            row = next(csvReader)
            if any(field.strip() for field in row):
                csvRows.append(row)
                readRows += 1
        except StopIteration:
            # End of file reached
            notEof = False
            break
        except Exception as e:
            print(f'Error reading CSV file: {e}')
            logging.error(f"Error reading CSV file: {e}")
            notEof = False
            break

    return readRows, csvRows

def nestedUserPart(currentUserPart, partIndex, parts, attributeValue):
    #######
    # Handle nested user parts
    #######

    #translationTable = str.maketrans({'\\':'\\\\','\"':'\\\"'})

    if partIndex < len(parts):
        #print(partIndex, " ", len(parts))
        part = parts[partIndex]
        if part not in currentUserPart:
            currentUserPart[part] = {}
            returnedPart = nestedUserPart(currentUserPart[part], partIndex + 1, parts, attributeValue)
            if returnedPart != '':
                currentUserPart[part] = returnedPart
            else:
                del currentUserPart[part]
            return currentUserPart
    else:
        currentUserPart = attributeValue
        #return currentUserPart.translate(translationTable)
        return currentUserPart

@sleep_and_retry
@limits(calls=100, period=1)  # Limit to 100 calls per second
def importUser(csvRow, csvHeaders, p1Geography, p1Environment, p1AT, p1DefaultPopulation, p1PasswordReset):
    #######
    # Import one user into PingOne
    #######

    #print("in import")

    #translationTable = str.maketrans({'\\':'\\\\','\"':'\\\"'})

    user = {}
    for headerIndex, header in enumerate(csvHeaders):
        if (header != "password") and \
           (header != "population") and \
           (header != "enabled"):
            if len(header.split('.')) > 1:
                # Handle nested headers
                parts = header.split('.')
                partIndex = 0
                if parts[0] not in user:
                    user[parts[0]] = {}
                returnedPart = nestedUserPart(user[parts[0]], partIndex+1, parts, csvRow[headerIndex])
                if returnedPart != '':
                    user[parts[0]] = returnedPart
            else:
                #user[header] = (csvRow[csvHeaders.index(header)].strip()).translate(translationTable)
                if(csvRow[csvHeaders.index(header)].strip() != ''):
                    user[header] = csvRow[csvHeaders.index(header)].strip()


    # handling enabled/disabled user
    if "enabled" in csvHeaders:
        if (csvRow[csvHeaders.index("enabled")].strip()).lower() == "true":
            user["enabled"] = True
        else:
            user["enabled"] = False

    # handling default population
    if "population" in csvHeaders:
        user["population"] = {}
        user["population"]["id"] = csvRow[csvHeaders.index("population")].strip()
    else:
        user["population"] = {}
        user["population"]["id"] = p1DefaultPopulation

    # handle password reset
    if "password" in csvHeaders:
        user["password"] = {}
        user["password"]["value"] = csvRow[csvHeaders.index("password")].strip()
        if(p1PasswordReset == "true"):
            user["password"]["forceChange"] = True
        else:
            user["password"]["forceChange"] = False


    # Call P1

    requestHeaders = {}
    requestHeaders['Authorization'] = 'Bearer ' + p1AT
    requestHeaders['Content-Type'] = 'application/vnd.pingidentity.user.import+json'
    requestBody = user


    
    try:
        createResponse = requests.post(f"https://api.pingone{p1Geography}/v1/environments/{p1Environment}/users", headers=requestHeaders, json=requestBody)
        if createResponse.status_code == 201:
            logging.info(f"User imported: {user['username']}")
        else:
            logging.error(f"Failed to import user {user['username']}: {createResponse.status_code} - {createResponse.text}")
    except Exception as e:
        logging.error(f"Error processing user {user['username']} - unable to continue: {e}")
        quit()

def printEnding(startTime, endTime):
    #######
    # Print the ending message
    #######

    print(f'PingOne User Import Utility - Ending')
    print(f'')
    logging.info(f"Ending import tool: {endTime}")
    
    totalTime = endTime - startTime
    print(f'Total time taken: {totalTime} ms')
    logging.info(f"Total time taken: {totalTime} ms")
    

def main():

    version = "0.2"
    workingDirectory = os.getcwd()
    configVersion = ""
    configWorkingDirectory = ""
    p1Environment = ""
    p1Geography = ""
    p1ClientId = ""
    p1ClientSecret = ""
    p1ClientType = ""
    tokenRefresh = ""
    csvPath = ""
    csvHeaders = []
    endOfCsv = False
    csvRows = []
    oneSecond = 1
    p1At = ""
    p1DefaultPopulation = ""
    p1PasswordReset = False
    startTime = 0
    lastTokenTime = 0
    nextToken = 0
    totalProcessed = 0
    
    startTime = printWelcome(version)
    configVersion, configWorkingDirectory, p1Environment, p1Geography, p1ClientId, p1ClientSecret, p1ClientType, tokenRefresh, p1DefaultPopulation, p1PasswordReset, csvPath = readConfigurationFile(workingDirectory, configVersion, configWorkingDirectory, p1Environment, p1Geography, p1ClientId, p1ClientSecret, p1ClientType, tokenRefresh, p1DefaultPopulation, p1PasswordReset, csvPath)
    checkWorkingDirectory(workingDirectory, configWorkingDirectory)
    checkVersion(configVersion, version)
    performClientTest(p1ClientId, p1ClientSecret, p1Geography, p1Environment, p1ClientType)
    ensureCsvExists(csvPath)
    csvHeaders, csvReader = readCsvHeaders(csvPath)
    p1At, lastTokenTime = getP1At(p1ClientId, p1ClientSecret, p1Geography, p1Environment, p1ClientType)
    nextToken = lastTokenTime + (tokenRefresh * 60 * 1000)
    try:
        with open(csvPath, 'r', newline='') as csvFile:
            csvFileReader = csv.reader(csvFile)
            headers = next(csvFileReader)
            while not endOfCsv:
                currentTime = int(time.time() * 1000)
                if currentTime > nextToken:
                    p1At, lastTokenTime = getP1At(p1ClientId, p1ClientSecret, p1Geography, p1Environment, p1ClientType)
                    nextToken = lastTokenTime + (tokenRefresh * 60 * 1000)
                csvRows = []
                threads = []
                numRead = 0
                numRead, csvRows = readNext100(csvFileReader)
                if numRead < 100:
                    endOfCsv = True
                for csvRow in csvRows:
                    t = threading.Thread(target=importUser, args=(csvRow, csvHeaders, p1Geography, p1Environment, p1At, p1DefaultPopulation, p1PasswordReset))
                    threads.append(t)
                    #importUser(csvRow, csvHeaders, p1Geography, p1Environment, p1At, p1DefaultPopulation, p1PasswordReset)
                ####
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                totalProcessed += numRead
                print(f'Processed: {totalProcessed}')
    except Exception as e:
        print(f'Error reading CSV file: {e}')
        logging.error(f"Error reading CSV file: {e}")
        quit()
    endTime = int(time.time() * 1000)
    printEnding(startTime, endTime)
    ##todo: add in token refresh logic
    ##todo: log start, finish, and total time in log file
    ##todo: create mfa tool

main()
