# PingOne User Import - Python Edition

### Disclaimer:
While these tools are written by Ping Identity field engineers, there is no official support granted or implied.  We use these in our day to day work and make them publicly available for use.  Feel free to file issues within the GitHub repository at github.com/jeremybcarrier/pingoneutilities to report issues or request features

## Description
This toolkit is for bulk importing users from a CSV file into PingOne.  

## More Detail
- This toolkit reads users from a comma-separated values (CSV) file and imports them into PingOne using PingOne APIs
- The first row in the CSV file should be a header column, and column names should match the PingOne attribute you will be mapping to (e.g. timezone, name.given, password)
- The only requisite field for a user is the username.  All other fields, including password, are optional
- The following default schema items are supported (see [https://apidocs.pingidentity.com/pingone/platform/v1/api/#user-operations] for details on required formats):
  - account
    - canAuthenticate
    - status
  - address
    - countryCode
    - locality
    - postalCode
    - region
    - streedAddress
  - email
  - enabled
  - lifcycle
    - status
    - suppressVerificationCode
  - locale
  - mobilePhone
  - name
    - family
    - formatted
    - given
    - honorificPrefix
    - honorificSuffix
    - middle
  - nickname
  - password (see [https://apidocs.pingidentity.com/pingone/platform/v1/api/#password-encoding] for password encoding requirements)
  - photo
    - href
  - population
    - id
  - preferredLanguage
  - primaryPhone
  - timezone
  - title
  - type
  - username
- Additionally, any custom string attributes you add to the schema are supported

<a name="anchor-prerequisites"></a>
## Prerequisites
Before you begin, you should:
- Have a working PingOne environment that is not the default Administrators environment
- Have a worker application with (at a minimum) **Environment Admin** and **Identity Data Admin** roles for your environment
- Have your PingOne *Environment ID* available
- Have your PingOne worker *Client ID* available
- Have your PingOne worker *Client Secret* available
- Have your PingOne Geography (.com, .eu, etc.) available
- A properly formatted CSV file for import (a sample is provided in this repository for testing)
- Identify a default population for imported users who do not have a population ID specified in the CSV and have this default population ID available

## Components
Three files are available in this repository

### example.csv
A sample CSV file for testing

### UserImportConfig.py
This is the configuration tool for the import.  It will:
1. Ask for your environment ID
2. Ask for your geography
3. Ask for your worker client ID
4. Ask for your worker client secret
5. Automatically determine if your worker is set to Authenticate via BASIC or POST
6. Ask you how often it should refresh your PingOne access token during import
  - PingOne worker tokens are valid for 60 minutes.  Large imports may take more than 60 minutes, so the tool can refresh your access token as needed.  The actual timing of the refresh can be anywhere between 1 and 59 minutes, but the default is 30 minutes
7. List all CSV files in the current working directory and ask you to specify the absolute path to your CSV
  - The default value is the first CSV found by the tool
8. Automatically check the headers in your CSV against the available attributes in your environment to ensure they match 
9. Ask if you want to force imported users to change their password at first login or not
10. List all available PingOne populations with their IDs and ask you to choose the default population for any users whose population is not specified in the CSV file
    - The default value is the first population returned by the PingOne API
11. Writes a configuration file in the current working directory called P1ImportUser.cfg

### UserImport.py
This is the actual script for importing.  It will:
1. Read the configuration file created by *UserImportConfig.py* out of the current working directory
2. Validate that the configuration file version matches the version of the import tool
3. Validate that all of the necessary fields are present in the configuration file
4. Validate that the working directory of the configuration file matches the current working directory
5. Validate that the tool can obtain a PingOne access token with the data from the configuration file
6. Validate that the CSV file specified in the configuration file is available
7. Read headers from the CSV and use them to map to PingOne attributes
8. Read 100 users at a time from the CSV
9. Import 100 users simultaneously via separate threads
10. Refresh the token based on the value provided during configuration
11. Ensure that the tool does not attempt to exceed the PingOne API rate limit of 100 API calls per second per IP address
12. Write the status of the import to a log file
13. Update the screen with user imports, 100 at a time

## How to Use
1) Ensure you have Python 3 installed
2) Download this repository to whatever working folder you choose
3) Ensure you have completed the prequisites(#anchor-prerequisites)
