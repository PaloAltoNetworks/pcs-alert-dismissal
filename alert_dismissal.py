#Helpers=======================================================================
#Get cloud account filter option suggestions
def get_cloud_account_filter_options(session, logger):
    logger.info(f'Getting Cloud Account Options')
    res = session.request('GET', '/filter/alert/suggest')
    return res.json()['cloud.account']['options']

#Get all policies from tenant
def get_policies_list_for_cloud_account_old(session, logger, cloud_type):
    logger.info('Getting all policies relevant to cloud account')
    res = session.request('GET', '/policy')
    data = res.json()

    #Get only policies relevant to the cloud account
    policy_list = [plc['policyId'] for plc in data if plc['cloudType'] == cloud_type or plc['cloudType'] == 'all']

    return policy_list

#Get policies for cloud account
def get_policies_list(session, logger, cloud_account):
    payload = {
        "detailed":False,
        "filters":[
            {"name":"timeRange.type","operator":"=","value":"ALERT_OPENED"},
            {"name":"alert.status","operator":"=","value":"open"},
            {"name": "alert.status", "operator":"=", "value": "snoozed"},
            {"name":"cloud.account","operator":"=","value":f"{cloud_account}"}
        ],
        "timeRange":{"type":"to_now","value":"epoch"}
        }
    
    logger.info(f'Getting policies for account \'{cloud_account}\'')
    res = session.request('POST', '/alert/policy', json=payload)

    data = res.json()

    policy_list = [plc['policyId'] for plc in data]

    return policy_list

def get_cloud_account_names(session, logger):
    logger.info(f'Getting All Cloud Account Names')
    res = session.request('GET', '/cloud/name')
    data = res.json()

    account_names = [acc['name'] for acc in data]

    return account_names


#V1==============================================================================

#Snooze alerts based on cloud account and polices
def snooze_alerts_mass(session, logger, cloud_account, policies):
    payload = {
        "alerts":[],
        "dismissalNote":"DISMISSAL SCRIPT",
        "dismissalTimeRange":{
            "type":"relative",
            "value":{
                "amount":"1",
                "unit":"hour"
            }
        },
       "filter":{
            "filters":[
                {"name":"timeRange.type","operator":"=","value":"ALERT_OPENED"},
                {"name":"alert.status","operator":"=","value":"open"},
                {"name":"cloud.account","operator":"=","value":f"{cloud_account}"}
            ],
            "timeRange":{"type":"to_now","value":"epoch"}
        },
        "policies":policies #this is a list of policy IDs
    }

    logger.info(f'Snoozing alerts for cloud account \'{cloud_account}\'')
    session.request('POST', '/alert/dismiss', json=payload)

#Snooze alerts based on cloud account and polices
def dismiss_alerts_mass(session, logger, cloud_account, policies):
    payload = {
        "alerts":[],
        "dismissalNote":"DISMISSAL SCRIPT",
        "filter":{
            "filters":[
                {"name":"timeRange.type","operator":"=","value":"ALERT_OPENED"},
                {"name":"alert.status","operator":"=","value":"open"},
                {"name":"cloud.account","operator":"=","value":f"{cloud_account}"}
            ],
            "timeRange":{"type":"to_now","value":"epoch"}
        },
        "policies":policies
    }

    logger.info(f'Dismissing alerts for cloud account \'{cloud_account}\'')
    session.request('POST', '/alert/dismiss', json=payload)

#Helper function for snoozing alerts en mass with one API call (not currently working)
def snooze_alerts_v1(session, logger, cloud_type, cloud_account, validate=False):
    if validate:
        cloud_names = get_cloud_account_names(session, logger)
        if cloud_account not in cloud_names:
            logger.error('Cloud Account name not found on tenant')
            return False
        else:
            logger.info(f'Cloud Account \'{cloud_account}\' ready to be dismissed')

    policies = get_policies_list(session, logger, cloud_account)
    snooze_alerts_mass(session, logger, cloud_account, policies)

def dismiss_alerts_v1(session, logger, cloud_type, cloud_account, validate=False):
    if validate:
        cloud_names = get_cloud_account_names(session, logger)
        if cloud_account not in cloud_names:
            logger.error('Cloud Account name not found on tenant')
            return False
        else:
            logger.info(f'Cloud Account \'{cloud_account}\' ready to be dismissed')

    policies = get_policies_list(session, logger, cloud_account)
    dismiss_alerts_mass(session, logger, cloud_account, policies)

    return True

#V2==============================================================================

#Get alerts
def get_alerts(session, logger, cloud_account):
    payload = {
        "filters":[
            {"name":"timeRange.type","operator":"=","value":"ALERT_OPENED"},
            {"name":"alert.status","operator":"=","value":"open"},
            {"name":"cloud.account","operator":"=","value":f"{cloud_account}"}
        ],
        "timeRange":{"type":"to_now","value":"epoch"},
        "limit": 20000,
        "offset": 0,
    }

    logger.info(f'Getting Alerts for cloud account {cloud_account}')
    res = session.request('POST', '/alert', json=payload)

    alert_ids = [al['id'] for al in res.json()]

    return alert_ids

def snooze_alerts_by_id(session, logger, cloud_account, policies, alerts):
    payload = {
    "alerts":alerts,
    "dismissalNote":"DISMISSAL SCRIPT",
    "dismissalTimeRange":{
        "type":"relative",
        "value":{
            "amount":"1",
            "unit":"hour"
        }
    },
    "filter":{
        "filters":[
            {"name":"timeRange.type","operator":"=","value":"ALERT_OPENED"},
            {"name":"alert.status","operator":"=","value":"open"},
            {"name":"cloud.account","operator":"=","value":f"{cloud_account}"}
        ],
        "timeRange":{"type":"to_now","value":"epoch"}
    },
    "policies":policies
    }

    logger.info(f'Snoozing \'{len(alerts)}\' alerts for cloud account \'{cloud_account}\'')
    session.request('POST', '/alert/dismiss', json=payload)

def dismiss_alerts_by_id(session, logger, cloud_account, policies, alerts):
    payload = {
    "alerts":alerts,
    "dismissalNote":"DISMISSAL SCRIPT",
    "filter":{
        "filters":[
            {"name":"timeRange.type","operator":"=","value":"ALERT_OPENED"},
            {"name":"alert.status","operator":"=","value":"open"},
            {"name":"cloud.account","operator":"=","value":f"{cloud_account}"}
        ],
        "timeRange":{"type":"to_now","value":"epoch"}
    },
    "policies":policies
    }

    logger.info(f'Dismissing \'{len(alerts)}\' alerts for cloud account \'{cloud_account}\'')
    session.request('POST', '/alert/dismiss', json=payload)