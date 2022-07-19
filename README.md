# PCS-ALERT-DISMISSAL

## Description

Script for dismissing Prisma Cloud Alerts from a Cloud Account after it has been deleted. This script is meant to be run every 6 hours as a cron job in order to ensure all Alerts are dismissed while the deleted Cloud Account is in its 24 hour data retention window.

# SET UP

## Installation

### Python3 and Pip3 

Python is a standard cross platform scripting language. Follow download and installation instructions from the Python Organization's website. https://www.python.org/downloads/.

Make sure to also install Pip3, Python3’s package manager so that the scripts required dependencies can be installed easily.

### Git and Repository Cloning

Install Git if it is not already installed on your machine. https://git-scm.com/book/en/v2/Getting-Started-Installing-Git

Clone this Git repo to your machine using:
```
git clone <repo clone url>
```

### Install script dependencies

Included in this repo is a requirements file. Use pip3 and this file to install all required Python dependencies: 
```
pip3 install -r requirements.txt
```

# USING THE SCRIPT

## Authentication

### Prisma Cloud Access Keys

The script authenticates with Prisma Cloud through Access Keys generated for the Tenant.

To generate an Access Key for a Prisma Cloud Tenant, navigate to settings -> Access Control -> Access Keys

![alt text](https://github.com/PaloAltoNetworks/pcs-alert-dismissal/blob/main/access_keys.png?raw=true)

Add an Access Key using the Add button drop down. Follow the steps and make note of the Access Key and the Secret key as this is the only time you will be able to see them. You will need the Access Key and Secret Key to authenticate the script with the Prisma Cloud Tenant.

### Prisma Cloud Stack URL

The correct API URL is needed to authenticate with a Prisma Cloud Tenant. The script can interpret the URL of a Prisma Cloud Tenant and turn it into a valid API URL so just copy the URL of the Tenant you want to authenticate with.

### Authenticating The Script

The combination of the Access Key, Secret Key, and API URL is all that is needed to authenticate the script with Prisma Cloud. When running the script, enter these values when prompted. 

## Script Command Line Arguments

### Running The Script

To run the script for the first time, run the following command:
```
python tenant_monitor.py -setup
```

To run the script and store Tenant credentials in a file for re-use, use the '-file' option:
```
python tenant_monitor.py -setup -file
```

After running the script for the first time, you no longer use the '-setup' option. This script is designed to be run as a cron job. The most common way this script will be run is:
```
python tenant_monitor.py -file
```

### Optional Arguments

Arguments do not have to be applied in any particular order and they can all be combined together. Just make sure that arguments that require parameters have the values passed to the command line right after the argument. This is seen in the Required Arguments examples.

_**-file**_  
By default, the authentication credentials are required to be supplied to the script each time the script is run. This is more secure as the plain text credentials are only stored in memory instead of in a file. However, if the user is repeatedly running the script, this authentication process is tedious. The user can supply a command line option, ‘-file’ that causes the script to write entered credentials out to a YAML file that will then be read from the next time the script is run saving time when the script is being run multiple times in a row. EX:
```
python tenant_monitor.py -file
```

_**-setup**_
To initialize the script and create the Cloud Account Data store, the '-setup' option is used. This should only need to be ran once.
```
python tenant_monitor.py -setup
```

_**-audit**_
Pulls down all Cloud Account data from the Tenant and calculates the changes in the Tenant between the last time the script was run and the current state. The script stops here and does not move forward with the cleanup process. No Cloud Accounts will be onboarded, no Alerts will be dismissed, no Cloud Accounts will be deleted.
```
python tenant_monitor.py -audit
or
python tenant_monitor.py -audit -file
```

_**-no_update**_
Once the script has run and the Alerts and Cloud Accounts have been cleaned up, the data store is updated and the current state of the tenant saved and marked as the previous state of the tenant so it is ready for the next time the script runs. The '-no_update' option stops this process. This is mainly used for debugging as the Alert clean up operation can be run over and over again on the same Cloud Accounts if the data store is not being updated after each run.
```
python tenant_monitor.py -no_update
or
python tenant_monitor.py -file -no_update
```

_**-limit**_
To avoid damage to the Tenant, there are a number of sanity checks included in the script. There is a limit to how many Cloud Accounts are processed at a time to help stop any widespread damage from happening. The default limit is 5 Cloud Accounts. To overwrite this limit, use the '-limit' option followed by the number of Accounts you want to set the limit too.
```
python tenant_monitor.py -limit 3
or
python tenant_monitor.py -limit 3 -file
```

_**-snooze**_
For testing the dismissal portion of the script, you can force the script to snooze alerts for one hour instead of dismissing alerts.
```
python tenant_monitor.py -snooze
or
python tenant_monitor.py -file -snooze
```
