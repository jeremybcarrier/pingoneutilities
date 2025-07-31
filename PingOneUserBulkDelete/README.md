# PingOne Bulk Delete

### Disclaimer:
While these tools are written by Ping Identity field engineers, there is no official support granted or implied.  We use these in our day to day work and make them publicly available for use.  Feel free to file issues within the GitHub repository at github.com/jeremybcarrier/pingoneutilities to report issues or request features

## Description
This toolkit is for bulk deletion of users in the PingOne platform

## More Detail
- This toolkit is designed to make bulk deletion of users based on a specific criteria.  Current options are:
  - Delete all users in an environment
  - Delete users in an environment's group
    - Note: Dynamic group filters in PingOne enable a wide variety of selection criteria - details at [https://docs.pingidentity.com/pingone/directory/p1_managing_groups.html]
  - Delete users who have not authenticated within a period of time (or never authenticated)
  - Delete users who have not completed email verification after a specific number of days since account creation

<a name="anchor-prerequisites"></a>
## Prerequisites
Before you begin, you should:
- Have a working PingOne environment 
- Have a worker application with (at a minimum) **Environment Admin** and **Identity Data Admin** roles for your environment
- Have your PingOne *Environment ID* available
- Have your PingOne worker *Client ID* available
- Have your PingOne worker *Client Secret* available
- Have your PingOne Geography (.com, .eu, etc.) available

## Components
A single python script

### P1BulkDelete.py
This script will:
1. Ask you for your PingOne environment information
2. Validate that it can obtain a PingOne access token with the data provided
3. Prompt you to choose deletion criteria
4. Perform deletion based on your criteria, with output to *P1UserDelete.log(

## How to Use
1. Ensure you have Python 3 installed with necessary [libraries](#anchor-libraries)
2. Download this repository to whatever working folder you choose
3. Ensure you have completed the [prequisites](#anchor-prerequisites)
4. Run the *P1BulkDeleet.py* script in your working directory
5. Review the results in your *P1UserDelete.log* file

<a name="anchor-libraries"></a>
## Python Libraries Used
1. requests [https://pypi.org/project/requests/]
   - Handles REST API calls to PingOne endpoints
2. os [https://docs.python.org/3/library/os.html]
   - Gets working diretory, searches for CSV files in the working directory, and ensures that the config and CSV file are present
3. base64 [https://docs.python.org/3/library/base64.html]
   - Handles encoding of client ID and secret for BASIC authentication
4. ratelimit [https://pypi.org/project/ratelimit/]
   - Ensures the script doesn't exceed the maximum transactions per second of PingOne APIs
5. logging [https://docs.python.org/3/library/logging.html]
   - Write the log file during import
8. concurrent.futures [https://docs.python.org/3/library/concurrent.futures.html]
   - Provides parallelism during import
9. time [https://docs.python.org/3/library/time.html]
   - Allows the script to get system time during operation for reporting and ensuring token refresh
10. re [https://docs.python.org/3/library/re.html]
    - Provides regex support to ensure inputs during configuration are in allowable formats
11. pwinput [https://pypi.org/project/pwinput/]
    - Hides the content of your client secret when you enter it
12. datetime [https://docs.python.org/3/library/datetime.html]
    - Provides date and time objects

