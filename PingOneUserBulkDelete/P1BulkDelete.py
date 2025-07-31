# PingOne Bulk Delete Tool
# Last Update: July 31, 2025
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
from datetime import datetime, timedelta

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
    print(f'4) Delete users who have not completed an account verification within a certain number of days of account creation')
    print(f'')

    deleteType = input(f'Please choose from the list above: ')

    if not deleteType:
        print(f'')
        print(f'*****************************************************************')
        print(f"Invalid selection, please retry.")
        print(f'*****************************************************************')
        print(f'')
        deleteType = getDeleteType()

    if deleteType in ['1', '2', '3', '4']:
        return deleteType
    else:
        print(f'')
        print(f'*****************************************************************')
        print(f"Invalid selection, please retry.")
        print(f'*****************************************************************')
        print(f'')
        deleteType = getDeleteType()

def getGroupSelection(p1At, p1Environment, p1Geography, guidFormat):
    ######
    # Get the list of P1 groups from the environment
    # If <50 groups exist, show them to the user, otherwise force the user to look it up
    # Get the group selection from the user
    ######

    requestHeaders = {}
    requestHeaders['Authorization'] = "Bearer " + p1At
    requestHeaders['Content-Type'] = 'application/json'
    requestUrl = f"https://api.pingone{p1Geography}/v1/environments/{p1Environment}/groups"

    try:
        response = requests.get(requestUrl, headers=requestHeaders)
        if response.status_code == 200:
            responseJson = response.json()
            groups = responseJson['_embedded']['groups']
            if len(groups) < 50:
                print(f'')
                print(f'Available groups in PingOne environment {p1Environment}:')
                for group in groups:
                    print(f"Group ID: {group['id']}, Group Name: {group['name']}")
                print(f'')
                groupId = input(f'Please enter the Group ID you want to delete users from: ')
                if re.match(guidFormat, groupId):
                    print(f'')
                    return groupId.lower()
                else:
                    # Group ID format is invalid, retry
                    print(f'')
                    print(f'************************************************************')
                    print(f'Error: The format of the Group ID is invalid, please retry.')
                    print(f'************************************************************')
                    print(f'')
                    groupId = getGroupSelection(p1At, p1Environment, p1Geography, guidFormat)
            else:
                print(f'')
                print(f'You have more than 50 groups in your PingOne environment.')
                print(f'Please look up the Group ID you want to delete users from and enter it below.')
                groupId = input(f'Please enter the Group ID you want to delete users from: ')
                if re.match(guidFormat, groupId):
                    print(f'')
                    return groupId.lower()
                else:
                    # Group ID format is invalid, retry
                    print(f'')
                    print(f'************************************************************')
                    print(f'Error: The format of the Group ID is invalid, please retry.')
                    print(f'************************************************************')
                    print(f'')
                    groupId = getGroupSelection(p1At, p1Environment, p1Geography, guidFormat)
        else:
            print(f'Error getting groups: {response.status_code} - {response.text}')
            infoLogger.error(f"Error getting groups: {response.status_code} - {response.text}")
            quit()
    except requests.exceptions.RequestException as e:
        print(f'Error connecting to PingOne: {e}')
        infoLogger.error(f"Error connecting to PingOne: {e}")
        quit()

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

def printDurationWarning():
    ######
    # Print a warning about the duration of the delete operation
    ######

    print(f'')
    print(f'WARNING: This operation may take some time based on the selected delete criteria.')
    print(f'')
    understand = input("Proceed? (yes/no): [yes]").strip().lower()
    
    if not understand:
        return True  # Default to yes if no input is provided
    if understand == 'yes':
        return True
    else:
        print(f'')
        print(f'Operation cancelled. Please run the tool again when you are ready.')
        quit()

def getLastLoginTimeSelection():
    ######
    # Get last login time selection from user input
    ######
    dateFormat = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"

    print(f'')
    print(f'This tool will remove users who have not logged in since a specified date.')
    print(f'Please enter the date and time in the format YYYY-MM-DD (e.g. 2023-07-28).')
    fullDate = input("Enter the date (YYYY-MM-DD): ")
    if re.match(dateFormat,fullDate):
        try:
            lastYear, lastMonth, lastDay = map(int, fullDate.split('-'))
            # Validate the date
            datetime.datetime(lastYear, lastMonth, lastDay)
            print(f'')
            print(f'Date validated: {lastYear}-{lastMonth:02d}-{lastDay:02d}.')
            print(f'')
            print(f'Do you also want to include users who have never logged in? (yes/no): [yes]')
            neverLogged = input().strip().lower()
            if not neverLogged:
                neverLogged = 'yes'  # Default to yes if no input is provided
                return lastDay, lastMonth, lastYear, True
            if neverLogged == 'yes':
                return lastDay, lastMonth, lastYear, True
            else:
                return lastDay, lastMonth, lastYear, False
        except ValueError:
            print(f'')
            print(f'Invalid date format or date does not exist.')
            lastDay, lastMonth, lastYear = getLastLoginTimeSelection()
    else:
        print(f'')
        print(f'Invalid date format.')
        lastDay, lastMonth, lastYear = getLastLoginTimeSelection()

def getCreateSelection():
    ######
    # Get number of days since account creation to check for verification
    ######

    print(f'')
    print(f'This tool will remove users who have not completed an account verification within a specified number of days account creation.')
    print(f'Please enter the number of days since account creation that an account should be allowed to remain unverified.')
    numDays = input("Days: [30] ")
    if not numDays:
        numDays = "30"
    else:
        if not (numDays.isdigit() and int(numDays) > 0):
            print(f'')
            print(f'Invalid input. Please enter a positive integer.')
            numDays = getCreateSelection()

    infoLogger.info(f"User verification check will be performed for accounts created more than {numDays} days ago.")
    return numDays

def getUsers(p1At, p1Environment, p1Geography, cursor, filter):    
    ######
    # Get page of users in PingOne Environment
    ######

    requestHeaders = {}
    requestHeaders['Authorization'] = "Bearer " + p1At
    requestHeaders['Content-Type'] = 'application/json'
    requestUrl = f"https://api.pingone{p1Geography}/v1/environments/{p1Environment}/users"
    if filter != "":
        requestUrl += f"?filter={filter}"
    
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

def deleteUser(user, p1Geography, p1Environment, p1At,):
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
            infoLogger.error(f"Error deleting user {userId}")
            detailedFailureLogger.error(f"Failed to delete user {userId}: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f'Error connecting to PingOne: {e}')
        infoLogger.error(f"Error connecting to PingOne: {e}")
        quit()

def deleteUserByLoginDate(user, p1Geography, p1Environment, p1At, msTime, neverLogged):
    ######
    # Deletes a user in PingOne Environment
    ######

    userHasLogged = False
    shouldDelete = False
    userLastLogin = 0

    if 'lastSignOn' in user:
        userHasLogged = True
        userDatePart = user['lastSignOn']['at'][0:10]
        dateTime = datetime.strptime(userDatePart, '%Y-%m-%d')
        dateTimeMs = int(dateTime.timestamp() * 1000)

    if (neverLogged == True) and (userHasLogged == False):
        shouldDelete = True

    if (neverLogged == False) and (userHasLogged):
        if msTime < dateTimeMs:
            shouldDelete = True

    if shouldDelete == True:
        # User should be deleted
        infoLogger.info(f"DELETING: user {user['username']} ({user['id']}).")
        deletingUser = deleteUser(user, p1Geography, p1Environment, p1At)
        return True
    else:
        # User should not be deleted
        infoLogger.info(f"SKIPPING: user {user['username']} ({user['id']}) does not meet delete criteria.")
        return False

def deleteUserByVerifyDate(user, p1Geography, p1Environment, p1At, msTime):
    ######
    # Deletes a user in PingOne Environment
    ######

    userStatusUnverified = False
    shouldDelete = False

    if user['lifecycle']['status'] == 'VERIFICATION_REQUIRED':
        userStatusUnverified = True
        createDatePart = user['createdAt'][0:10]
        createDateTime = datetime.strptime(createDatePart, '%Y-%m-%d')
        createDateTimeMs = int(createDateTime.timestamp() * 1000)
        if createDateTimeMs < msTime:
            infoLogger.info(f"DELETING: User {user['id']} is in VERIFICATION_REQUIRED status and created before {msTime}.")
            deletingUser = deleteUser(user, p1Geography, p1Environment, p1At)
            #########DO DELETE#########
            return True
        else:
            infoLogger.info(f"SKIPPING: User {user['id']} is in VERIFICATION_REQUIRED status but created after {msTime}.")
    else:
        infoLogger.info(f"SKIPPING: User {user['id']} is not in VERIFICATION_REQUIRED status.")
        return False

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

def main():

    version = "0.1"
    workingDirectory = os.getcwd()
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
    filter = ""
    specialFilter = False
    lastYear = 0
    lastMonth = 0
    lastDay = 0
    understandDuration = False
    numDaysSinceCreate = 0
    
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
        # All P1
        case '1':
            filter = ""
            specialFilter = False
        # P1 Group
        case '2':
            groupId = getGroupSelection(p1At, p1Environment, p1Geography, guidFormat)
            filter = f'memberOfGroups[id eq "{groupId}"]'
            specialFilter = False
        # P1 Last Login Date or never logged in
        case '3':
            understandDuration = printDurationWarning()
            if understandDuration == True:
                # get date, get users who match, include users who have never logged in
                lastDay, lastMonth, lastYear, neverLogged = getLastLoginTimeSelection()
                dateObject = datetime.datetime(lastYear, lastMonth, lastDay, 0, 0, 0)
                msTime = dateObject.timestamp() * 1000
                print(f'')
                specialFilter = True
                try:
                    while cursor != "":
                        currentUserList, cursor, readCount = getUsers(p1At, p1Environment, p1Geography, cursor, "")
                        print(cursor)
                        currentTime = int(time.time() * 1000)
                        if currentTime > nextToken:
                            p1At, lastTokenTime = getP1At(p1ClientId, p1ClientSecret, p1Geography, p1Environment, p1ClientType)
                            nextToken = lastTokenTime + (tokenRefresh * 60 * 1000)
                        threads = []
                        for user in currentUserList:
                            thread = executor.submit(deleteUserByLoginDate, user, p1Geography, p1Environment, p1At, msTime, neverLogged)
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
                    print(f'Error deleting users: {e}')
                    infoLogger.error(f"Error deleting users: {e}")
                    quit()
        case '4':
            # Get the number of days since account creation to check for verification
            numDaysSinceCreate = int(getCreateSelection())
            today = datetime.now()
            past_date = today - timedelta(days=numDaysSinceCreate)
            msTime = past_date.timestamp() * 1000
            print(f'')
            specialFilter = True
            try:
                while cursor != "":
                    currentUserList, cursor, readCount = getUsers(p1At, p1Environment, p1Geography, cursor, "")
                    #print(cursor)
                    currentTime = int(time.time() * 1000)
                    if currentTime > nextToken:
                        p1At, lastTokenTime = getP1At(p1ClientId, p1ClientSecret, p1Geography, p1Environment, p1ClientType)
                        nextToken = lastTokenTime + (tokenRefresh * 60 * 1000)
                    threads = []
                    for user in currentUserList:
                        thread = executor.submit(deleteUserByVerifyDate, user, p1Geography, p1Environment, p1At, msTime)
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
                print(f'Error deleting users: {e}')
                infoLogger.error(f"Error deleting users: {e}")
                quit()
        case _:
            print(f'')
            print(f'*****************************************************************')
            print(f"Invalid selection, please retry.")
            print(f'*****************************************************************')
            print(f'')

    if specialFilter == False:
        try:
            while cursor != "":
                currentUserList, cursor, readCount = getUsers(p1At, p1Environment, p1Geography, cursor, filter)
                print(cursor)
                currentTime = int(time.time() * 1000)
                if currentTime > nextToken:
                    p1At, lastTokenTime = getP1At(p1ClientId, p1ClientSecret, p1Geography, p1Environment, p1ClientType)
                    nextToken = lastTokenTime + (tokenRefresh * 60 * 1000)
                threads = []
                for user in currentUserList:
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
            print(f'Error deleting users: {e}')
            infoLogger.error(f"Error deleting users: {e}")
            quit()

    endTime = int(time.time() * 1000)
    printEnding(startTime, endTime)

main()

