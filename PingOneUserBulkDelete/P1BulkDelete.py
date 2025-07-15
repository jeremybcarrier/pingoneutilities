# PingOne Bulk Delete Tool
# Last Update: July 15, 2025
# Authors: Jeremy Carrier

import requests
import os
import base64
from ratelimit import limits, sleep_and_retry
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import pwinput

logFormat = logging.Formatter("%(asctime)s - %(message)s")

# Setup info logging
handler = logging.FileHandler("P1UserDelete.log")
handler.setFormatter(logFormat)
infoLogger = logging.getLogger("mainLog")
infoLogger.setLevel(logging.INFO)
infoLogger.addHandler(handler)

# Setup error logging
handler = logging.FileHandler("P1UserDeleteFailuresDetail.log")
handler.setFormatter(logFormat)
detailedFailureLogger = logging.getLogger("dFLog")
detailedFailureLogger.setLevel(logging.ERROR)
detailedFailureLogger.addHandler(handler)

def printWelcome(version):
    #######
    # Print the welcome message
    #######

    startTime = int(time.time() * 1000) 
    
    print(f'')
    print(f'********************************************')
    print(f'PingOne User Delete Utility - version {version}')
    print(f'********************************************')
    print(f'')
    print(f'Actions will be written to the log file P1UserDelete.log')
    print(f'')
    print(f'This tool will walk you through the configuration of the User Delete Tool.  You will need the following:')
    print(f'1) Your PingOne Environment ID')
    print(f'2) Your PingOne Geography')
    print(f'3) A PingOne Worker Client ID and Client Secret')
    
    infoLogger.info(f"PingOne User Delete Utility - version {version}")
    infoLogger.info(f"Starting delete tool: {startTime}")

    return startTime

def getP1Environment(p1Environment, guidFormat):
    # *********
    # Prompts the user for the PingOne Environment ID and validates its format.
    # *********
    print(f'')
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
    print(f'')
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
    print(f'')
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
    print(f'')
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
            infoLogger.info(f"Successfully connected to PingOne client with BASIC auth.")
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
            infoLogger.info(f"Successfully connected to PingOne client with POST auth.")
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

def getDeleteType():
    # *********
    # Prompts the user for the options for deletion.
    # *********

    print(f'')
    print(f'Please select the type of delete you want to perform:')
    print(f'1) Delete all users in the PingOne environment')
    print(f'2) Delete users in a group in the PingOne environment')
    print(f'3) Delete users whose last login time was before a certain date')
    print(f'')

    deleteType = input(f'Please choose from the list above: ')

    if not deleteType:
        print(f'')
        print(f'*****************************************************************')
        print(f"Invalid selection, please retry.")
        print(f'*****************************************************************')
        print(f'')
        deleteType = getDeleteType()

    if deleteType in ['1', '2', '3']:
        return deleteType
    else:
        print(f'')
        print(f'*****************************************************************')
        print(f"Invalid selection, please retry.")
        print(f'*****************************************************************')
        print(f'')
        deleteType = getDeleteType()

def getP1At(p1ClientId, p1ClientSecret, p1Geography, p1Environment, p1ClientType):
    #######
    # Get the access token from PingOne
    #######

    tokenTime = int(time.time() * 1000)

    print(f'Getting access token from PingOne at {tokenTime}.')
    infoLogger.info(f"Getting access token from PingOne at {tokenTime}.")
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
            infoLogger.error(f"Error getting access token: {response.status_code} - {response.text}")   
            quit()
    except requests.exceptions.RequestException as e:
        print(f'Error connecting to PingOne: {e}')
        infoLogger.error(f"Error connecting to PingOne: {e}")
        quit()

def getExistingUsercount(p1At, p1Environment, p1Geography):
    ######
    # Get existing user count in PingOne Environment
    ######

    requestHeaders = {}
    requestHeaders['Authorization'] = "Bearer " + p1At

    try: 
        getCurrentUsers = requests.get(f"https://api.pingone{p1Geography}/v1/environments/{p1Environment}/users",headers=requestHeaders)

        if getCurrentUsers.status_code == 200:
            currentUserCount = getCurrentUsers.json()['count']
            print(f'')
            print(f'Current user count in PingOne environment {p1Environment} is: {currentUserCount}')
            print(f'')
            infoLogger.info(f'Current user count in PingOne environment {p1Environment} is: {currentUserCount}')
    except:
        infoLogger.error("Error: Unable to read existing users using worker access token.")
        print(f'')
        print(f'************************************************************************************************************************')
        print("Failed to read the existing users of your PingOne environment.  Please ensure your worker has appropriate rights.  Exiting.")
        print(f'************************************************************************************************************************')
        print(f'')
        quit()

    return currentUserCount

def getUsers(p1At, p1Environment, p1Geography, cursor):    
    ######
    # Get page of users in PingOne Environment
    ######

    requestHeaders = {}
    requestHeaders['Authorization'] = "Bearer " + p1At
    requestHeaders['Content-Type'] = 'application/json'
    requestUrl = f"https://api.pingone{p1Geography}/v1/environments/{p1Environment}/users"
    
    if cursor is not None:
        requestUrl = cursor

    try:
        response = requests.get(requestUrl, headers=requestHeaders)
        if response.status_code == 200:
            print(f"User page retrieved.")
            print(f'')
            infoLogger.info(f"User page retrieved.")
            responseJson = response.json()
            users = responseJson['_embedded']['users']
            if '_links' in responseJson:
                if 'next' in responseJson['_links']:
                    cursor = responseJson['_links']['next']['href']
                else:
                    cursor = ""
            return users, cursor, responseJson['size']
        else:
            print(f'Error getting users: {response.status_code} - {response.text}')
            infoLogger.error(f"Error getting users: {response.status_code} - {response.text}")
            quit()
    except requests.exceptions.RequestException as e:
        print(f'Error connecting to PingOne: {e}')
        infoLogger.error(f"Error connecting to PingOne: {e}")
        quit()

def deleteUser(user, p1Geography, p1Environment, p1At):
    ######
    # Deletes a user in PingOne Environment
    ######

    requestHeaders = {}
    requestHeaders['Authorization'] = "Bearer " + p1At
    requestHeaders['Content-Type'] = 'application/json'

    try:
        userId = user['id']
        deleteUrl = f"https://api.pingone{p1Geography}/v1/environments/{p1Environment}/users/{userId}"
        response = requests.delete(deleteUrl, headers=requestHeaders)
        
        if response.status_code == 204:
            infoLogger.info(f"User {userId} deleted successfully.")
            return True
        else:
            #print(f'Error deleting user {userId}: {response.status_code} - {response.text}')
            infoLogger.error(f"Error deleting user {userId}")
            detailedFailureLogger.error(f"Failed to delete user {userId}: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f'Error connecting to PingOne: {e}')
        infoLogger.error(f"Error connecting to PingOne: {e}")
        quit()

def printEnding(startTime, endTime):
    #######
    # Print the ending message
    #######

    print(f'PingOne User Delete Utility - Ending')
    print(f'')
    infoLogger.info(f"Ending delete tool: {endTime}")

    totalTime = endTime - startTime
    print(f'Total time taken: {totalTime} ms')
    infoLogger.info(f"Total time taken: {totalTime} ms")


# Get config info*
# validate info*
# do delete


def main():

    version = "0.1"
    workingDirectory = os.getcwd()
    #configVersion = ""
    #configWorkingDirectory = ""
    guidFormat = r"^[a-fA-f0-9]{8}-[a-fA-f0-9]{4}-[a-fA-f0-9]{4}-[a-fA-f0-9]{4}-[a-fA-f0-9]{12}$"
    p1Environment = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    p1Geography = ""
    p1ClientId = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    p1ClientSecret = ""
    p1ClientTest = False
    p1ClientType = "failed"
    tokenRefresh = ""
    oneSecond = 1
    p1At = ""
    startTime = 0
    lastTokenTime = 0
    nextToken = 0
    totalProcessed = 0
    currentUserCount = 0
    successfulDelete = 0
    failedDelete = 0
    executor = ThreadPoolExecutor(max_workers=100)
    deleteType = ""
    currentUserList = []
    cursor = None
    readCount = 0
    totalProcessed = 0
    
    startTime = printWelcome(version)
    while (p1ClientTest == False) and \
          (p1ClientType == "failed"):
        p1Environment = getP1Environment(p1Environment, guidFormat)
        p1Geography = getP1Geo()
        p1ClientId = getP1ClientId(p1ClientId, guidFormat)
        p1ClientSecret = getP1ClientSecret()
        p1ClientType, p1At = getP1ClientType(p1ClientId, p1ClientSecret, p1Geography, p1Environment)
        if (p1ClientType != "failed"):
            tokenRefresh = getTokenRefreshDuration()
    deleteType = getDeleteType()
    p1At, lastTokenTime = getP1At(p1ClientId, p1ClientSecret, p1Geography, p1Environment, p1ClientType)
    nextToken = lastTokenTime + (int(tokenRefresh) * 60 * 1000)
    currentUserCount = getExistingUsercount(p1At, p1Environment, p1Geography)

    match deleteType:
        case '1':
            try:
                while cursor != "":
                    currentUserList, cursor, readCount = getUsers(p1At, p1Environment, p1Geography, cursor)
                    print(cursor)
                    currentTime = int(time.time() * 1000)
                    if currentTime > nextToken:
                        p1At, lastTokenTime = getP1At(p1ClientId, p1ClientSecret, p1Geography, p1Environment, p1ClientType)
                        nextToken = lastTokenTime + (tokenRefresh * 60 * 1000)
                    threads = []
                    for user in currentUserList:
                        #print(user)
                        thread = executor.submit(deleteUser, user, p1Geography, p1Environment, p1At)
                        threads.append(thread)
                    for thread in as_completed(threads):
                        try:
                            threadResult = thread.result()
                            if threadResult == True:
                                successfulDelete += 1
                            else:
                                failedDelete += 1
                        except Exception as e:
                            print(f"Thread generated an exception: {e}")
                            infoLogger.error(f"Error: Thread generated an exception: {e}")
                    totalProcessed += readCount
            except Exception as e:
                print(f'Error deleting all users: {e}')
                infoLogger.error(f"Error deleting all users: {e}")
                quit()
        case '2':
            ####START HERE
            # do specific group
            print(f'')
        case '3':
            # get date, get users who match, include users who have never logged in
            print(f'')
        case _:
            print(f'')
            print(f'*****************************************************************')
            print(f"Invalid selection, please retry.")
            print(f'*****************************************************************')
            print(f'')

    endTime = int(time.time() * 1000)
    printEnding(startTime, endTime)

#need more logging

main()

