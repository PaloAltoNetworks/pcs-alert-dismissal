from loguru import logger
import sys
from sdk.load_config import load_config_create_session
import alert_dismissal
import json
import os
import time
import re
import datetime

#Get AWS org child accounts====================================================
#This function makes API calls to get full details of each child cloud account
def aws_get_child_accounts(session,accountID,cloudType, logger):
    logger.info(f'Getting child accounts for \'{accountID}\'.')
    res = session.request('GET', f'cloud/{cloudType}/{accountID}/project')
    child_account_data = res.json()

    child_accounts_list = []

    #Extract only the needed data
    for acc in child_account_data:
        if acc['accountType'] != 'organization':
            account_details = get_cloud_account_details(session, acc['accountId'], acc['cloudType'], logger)

            name = acc['name']

            #Account ID regex
            if not re.search(r"^[0-9]{12}$", acc['accountId']):
                logger.warning(f'Cloud account \'{name}\' has invalid Account ID. Skipping...')
                continue

            #Role ARN regex
            if not re.search(r":[0-9]{12}:", account_details['roleArn']):
                logger.warning(f'Cloud account \'{name}\' has invalid Role ARN. Skipping...')
                continue

            cloud_account = {
                'accountID': acc['accountId'],
                'accountName': acc['name'],
                'groupIDs': acc['groupIds'],
                'externalID': account_details['externalId'],
                'roleARN': account_details['roleArn'],
                'cloudType': acc['cloudType'],
                'accountType': acc['accountType'],
                'childOfOrg': True,
                'parentID': accountID
            }

            child_accounts_list.append(cloud_account)

    return child_accounts_list

#Extracts only the needed data for each cloud account==========================
#Gets all child accounts related to an org and all other needed infomation
def process_aws_cloud_accounts_dump(cloud_accounts_data, logger):
    cloud_accounts_list = []

    for acc in cloud_accounts_data:
        if acc['cloudType'] != 'aws':
            continue

        account_details = get_cloud_account_details(session, acc['accountId'], acc['cloudType'], logger)

        name = acc['name']

        #Account ID regex
        if not re.search(r"^[0-9]{12}$", acc['accountId']):
            logger.warning(f'Cloud account \'{name}\' has invalid Account ID. Skipping...')
            continue

        #Role ARN regex
        if not re.search(r":[0-9]{12}:", account_details['roleArn']):
            logger.warning(f'Cloud account \'{name}\' has invalid Role ARN. Skipping...')
            continue

        cloud_account = {
            'accountID': acc['accountId'],
            'accountName': acc['name'],
            'groupIDs': acc['groupIds'],
            'externalID': account_details['externalId'],
            'roleARN': account_details['roleArn'],
            'cloudType': acc['cloudType'],
            'accountType': acc['accountType'],
            'childOfOrg': False,
            'numChildAccounts': acc['numberOfChildAccounts'],
            'childAccounts': []
        }
        if acc['numberOfChildAccounts'] > 0:
            child_accounts_list = aws_get_child_accounts(session, acc['accountId'], acc['cloudType'], logger)
            child_accounts_ids = [acc['accountID'] for acc in child_accounts_list]
            cloud_account['childAccounts'] = child_accounts_ids

            cloud_accounts_list.append(cloud_account)
            cloud_accounts_list.extend(child_accounts_list)

        else:
            cloud_accounts_list.append(cloud_account)

    return cloud_accounts_list

#Gets a cloud accounts full details============================================
#To get role arns and external ids for each cloud account, an additional API call is needed
def get_cloud_account_details(session, accountID, cloudType, logger):
    logger.info(f'Getting cloud account data for \'{cloudType}\' account ID \'{accountID}\'.')
    res = session.request('GET', f'/cloud/{cloudType}/{accountID}')
    return res.json()

#Function for establishing cloud account state for first time==================
#Creates pre_cloud_accounts.json file so that there is a baseline for subsequent runs. 
def first_time_setup(session, logger):
    f_path = os.path.join('cloud_accounts_data', 'prev_cloud_accounts.json')
    if os.path.exists(f_path):
        logger.error('prev_cloud_accounts.json file already exists. Can\'t complete first time setup.')
        return

    #Get all cloud accounts on the tenant
    logger.info('Getting all cloud accounts from tenant')
    res = session.request('GET', 'cloud')
    cloud_account_dump = res.json()

    #Create data store as a json file.
    aws_cloud_account_data = process_aws_cloud_accounts_dump(cloud_account_dump, logger)
    f_path = os.path.join('cloud_accounts_data', 'prev_cloud_accounts.json')
    with open(f_path, 'w') as outfile:
        json.dump(aws_cloud_account_data, outfile)

#Gets most recent list of cloud accounts on tenant=============================
#Gets the current state of the cloud accounts to be compared against the previous state of the tenant.
def get_curr_cloud_accounts(session, logger):
    #Get all cloud accounts on the tenant
    logger.info('Getting all cloud accounts from tenant')
    res = session.request('GET', 'cloud')
    cloud_account_dump = res.json()

    #Get just AWS accounts that have only the required data for the scripts usage.
    aws_cloud_account_data = process_aws_cloud_accounts_dump(cloud_account_dump, logger)

    #Output current cloud accounts data store as a json file
    f_path = os.path.join('cloud_accounts_data', 'curr_cloud_accounts.json')
    with open(f_path, 'w') as outfile:
        json.dump(aws_cloud_account_data, outfile)

#Gets list of cloud accounts no longer on tenant===============================
#Compares prev and curr cloud accounts to find ones that have been recently deleted
#and need to have their alerts cleaned up.
def get_cloud_accounts_diff(session, logger, del_limit=5):
    #Get all cloud accounts on the tenant
    get_curr_cloud_accounts(session, logger)

    #Read in curr cloud accounts
    curr_cloud_account_data = {}
    f_path = os.path.join('cloud_accounts_data', 'curr_cloud_accounts.json')
    with open(f_path, 'r') as infile:
        curr_cloud_account_data = json.load(infile)
    
    #Create list of curr IDs
    curr_ids = [acc['accountID'] for acc in curr_cloud_account_data]

    #Read in prev cloud accounts
    prev_cloud_account_data = {}
    f_path = os.path.join('cloud_accounts_data', 'prev_cloud_accounts.json')
    with open(f_path, 'r') as infile:
        prev_cloud_account_data = json.load(infile)

    #Create list of prev IDs
    prev_ids = [acc['accountID'] for acc in prev_cloud_account_data]

    #Create list of IDs of the deleted cloud accounts
    deleted_ids = []
    for p_id in prev_ids:
        if p_id not in curr_ids:# account has been deleted
            deleted_ids.append(p_id)

    #Create a list of cloud account data structures for the deleted accounts
    deleted_accounts = []
    for d_id in deleted_ids:
        for acc in prev_cloud_account_data:
            if acc['accountID'] == d_id:
                deleted_accounts.append(acc)

    #Output information
    logger.info('Previous Cloud Accounts Count: ' + str(len(prev_cloud_account_data)))
    logger.info('Current Cloud Accounts Count: ' + str(len(curr_cloud_account_data)))
    logger.info('Cloud Accounts Difference Count: ' + str(len(deleted_accounts)))

    #Output accounts to delete data store as a json file
    f_path = os.path.join('cloud_accounts_data', 'accounts_to_cleanup.json')
    with open(f_path, 'w') as outfile:
        json.dump(deleted_accounts, outfile)
    
    #Check to make sure deleted account count is within boundries
    if len(deleted_accounts) > del_limit:
        exit()

    return deleted_accounts

#Driver function for onboarding, dismissing alerts, and deleting
def cleanup_cloud_accounts(session, accounts_to_cleanup, snooze:bool, logger):
    if len(accounts_to_cleanup) <= 0:
        return

    successfully_onboarded_accounts = re_onboard_cloud_accounts(session, accounts_to_cleanup, logger)

    time.sleep(5)#Give time for accounts to onboard

    #Use list of succesffuly onboarded accounts instead of accounts_to_cleanup
    dismiss_alerts_for_cloud_accounts(session, successfully_onboarded_accounts, snooze, logger)
    deleted_re_onbaorded_cloud_accounts(session, successfully_onboarded_accounts, logger)

def audit_logging(accounts_to_cleanup):
    f_path = os.path.join('logs','audit_logs','cloud_accounts_to_process.json')
    with open(f_path, 'a') as outfile:
        outfile.write('\n\n' + str(datetime.datetime.now()) + '\n')

    for account in accounts_to_cleanup:
        with open(f_path, 'a') as outfile:
            json.dump(account, outfile)
            outfile.write('\n\n')
    

def re_onboard_cloud_accounts(session, accounts_to_onboard, logger):
    #output each succesffully re-onboarded account
    f_path = os.path.join('logs','tenant_state_recovery','re_onboarded_accounts.json')
    with open(f_path, 'a') as outfile:
        outfile.write('\n\n' + str(datetime.datetime.now()) + '\n')

    f_path_failed = os.path.join('logs','tenant_state_recovery','failed_re_onboarded_accounts.json')
    with open(f_path_failed, 'a') as outfile:
        outfile.write('\n\n' + str(datetime.datetime.now()) + '\n')

    success_onborded = []

    for account in accounts_to_onboard:
        payload = {
            "accountId":account['accountID'],
            "accountType":"account",
            "enabled":True,
            "externalId":account['externalID'],
            "groupIds":account['groupIDs'],
            "name":account['accountName'],
            "protectionMode":"MONITOR",
            "roleArn":account['roleARN'],
            "storageScanEnabled":False,
            "vulnerabilityAssessmentEnabled":False
        }
        querystring = {"skipStatusChecks":1}

        name = account['accountName']
        logger.info(f'Onboarding Cloud Account: \'{name}\'')
        res = session.request('POST', 'cloud/aws', json=payload, params=querystring)

        if res.status_code == 200:
            with open(f_path, 'a') as outfile:
                json.dump(account, outfile)
                outfile.write('\n\n')
            success_onborded.append(account)
        else:
            with open(f_path_failed, 'a') as outfile:
                json.dump(account, outfile)
                outfile.write('\n\n')

        return success_onborded

def dismiss_alerts_for_cloud_accounts(session, accounts_to_dismiss, snooze, logger):
    f_path = os.path.join('logs','tenant_state_recovery','dismissed_accounts.json')
    with open(f_path, 'a') as outfile:
        outfile.write('\n\n' + str(datetime.datetime.now()) + '\n')

    f_path_failed = os.path.join('logs','tenant_state_recovery','failed_dismissed_accounts.json')
    with open(f_path_failed, 'a') as outfile:
        outfile.write('\n\n' + str(datetime.datetime.now()) + '\n')

    for account in accounts_to_dismiss:
        cloud_type = account['cloudType']
        cloud_name = account['accountName']

        if snooze:
            res = alert_dismissal.snooze_alerts_v1(session, logger, cloud_type, cloud_name, True)
        else:
            res = alert_dismissal.dismiss_alerts_v1(session, logger, cloud_type, cloud_name, True)

        if res == True:
            with open(f_path, 'a') as outfile:
                json.dump(account, outfile)
                outfile.write('\n\n')
        else:
            with open(f_path_failed, 'a') as outfile:
                json.dump(account, outfile)
                outfile.write('\n\n')

def deleted_re_onbaorded_cloud_accounts(session, accounts_to_delete, logger):
    f_path = os.path.join('logs','tenant_state_recovery','re_deleted_accounts.json')
    with open(f_path, 'a') as outfile:
        outfile.write('\n\n' + str(datetime.datetime.now()) + '\n')

    f_path_failed = os.path.join('logs','tenant_state_recovery','failed_re_deleted_accounts.json')
    with open(f_path_failed, 'a') as outfile:
        outfile.write('\n\n' + str(datetime.datetime.now()) + '\n')

    for account in accounts_to_delete:
        cloud_type = account['cloudType']
        c_id = account['accountID']
        name = account['accountName']
        logger.info(f'Deleting Account: \'{name}\'')
        res = session.request('DELETE', f'/cloud/{cloud_type}/{c_id}')
        if res.status_code == 200:
            with open(f_path, 'a') as outfile:
                json.dump(account, outfile)
                outfile.write('\n\n')
        else:
            with open(f_path_failed, 'a') as outfile:
                json.dump(account, outfile)
                outfile.write('\n\n')

def update_curr_and_prev_accounts_json(session, logger):
    curr_accounts = []
    f_path = os.path.join('cloud_accounts_data', 'curr_cloud_accounts.json')
    with open(f_path, 'r') as infile:
        curr_accounts = json.load(infile)

    prev_accounts = []
    f_path = os.path.join('cloud_accounts_data', 'prev_cloud_accounts.json')
    with open(f_path, 'r') as infile:
        prev_accounts = json.load(infile)

    #Write curr accounts to prev accounts
    f_path = os.path.join('cloud_accounts_data', 'prev_cloud_accounts.json')
    with open(f_path, 'w') as outfile:
        json.dump(curr_accounts, outfile)

    #Write prev accounts to old prev accounts
    f_path = os.path.join('cloud_accounts_data', 'old_prev_cloud_accounts.json')
    with open(f_path, 'w') as outfile:
        json.dump(prev_accounts, outfile)
    

#Main script functions---------------------------------------------------------
if __name__ == '__main__':
    args = [el.lower() for el in sys.argv]

    arg_list = ['-file', '-setup', '-audit','-no_update', '-limit', '-snooze']

    #Validate arguments 
    for arg in args:
        if arg[0] == '-':
            if arg not in arg_list:
                logger.error(f'Uknown option in command line: \'{arg}\'')
                exit()

    #Add checks for valid arguments

    #TODO add file output for logs

    file_mode = False
    if '-file' in args:
        file_mode = True

    setup_mode = False
    if '-setup' in args:
        setup_mode = True

    audit_mode = False
    if '-audit' in args:
        audit_mode = True

    no_update = False
    if '-no_update' in args:
        no_update = True

    snooze = False
    if '-snooze' in args:
        snooze = True

    del_limit = 5
    if '-limit' in args:
        try:
            del_limit = int(args[args.index('-limit')+1])
        except:
            logger.error('Missing account_limit value')
            exit()

    session = load_config_create_session(file_mode, logger)

    if setup_mode == True:
        first_time_setup(session, logger)
    else:
        cloud_accounts_to_cleanup = get_cloud_accounts_diff(session, logger, del_limit)

        if audit_mode == False:
            cleanup_cloud_accounts(session, cloud_accounts_to_cleanup, snooze, logger)
        else:#audit mode == true
            audit_logging(cloud_accounts_to_cleanup)

        if no_update == False:
            update_curr_and_prev_accounts_json(session, logger)




    #Load past cloud accounts into memory

    #Compare list of cloud accounts

    #Get list of cloud accounts that are now missing

    #Do a santiy check for missing cloud accounts, if more than say 5, thats too many for a given time period.

    #Re-onboard recently deleted cloud accounts

    #Dismiss all alerts for thoese cloud accounts

    #Re-delete those cloud accounts.


    #Notes

    #Check to make sure the cloud accounts record has not been deleted

    #For each deleted cloud account, create a temp record of all the cloud accounts so in case the script crashes mid execuation, there is a way to recover the tenant's state.

    #All actions taken by script need to be recorded so that any change can be undone. Each log record needs to not only include a description of what was done but also enough information that the action could be repeated manully by a person or undone by a person.

