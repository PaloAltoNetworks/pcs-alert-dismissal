from os import path
import re
import yaml
from sdk.session_manager import Session
from sdk.color_print import c_print
import requests
import json

def validate_credentials(a_key, s_key, url) -> bool:
    '''
    This function creates a session with the supplied credentials to test 
    if the user successfully entered valid credentails.
    '''

    headers = {
    'content-type': 'application/json; charset=UTF-8'
    }

    payload = {
        "username": f"{a_key}",
        "password": f"{s_key}"
    }

    try:
        c_print('API - Validating credentials')
        response = requests.request("POST", f'{url}/login', headers=headers, json=payload)

        if response.status_code == 200:
            c_print('SUCCESS', color='green')
            print()
            return True
        else:
            return False
    except:
        c_print('ERROR', end=' ', color='red')
        print('Could not connect to Prisma Cloud API.')
        print()
        print('Steps to troubleshoot:')
        c_print('1) Please disconnect from any incompatible VPN', color='blue')
        print()
        c_print('2) Please ensure you have entered a valid Prisma Cloud URL.', color='blue')
        print('EX: https://app.prismacloud.io or https://app2.eu.prismacloud.io')
        print()
        return False

#==============================================================================

def validate_url(url):
    if len(url) >= 3:
        if 'https://' not in url:
            if url[:3] == 'app' or url[:3] == 'api':
                url = 'https://' + url
            
    
    url = url.replace('app', 'api')

    url = re.sub(r'prismacloud\.io\S*', 'prismacloud.io', url)

    return url

#==============================================================================

def get_tenant_credentials():

    c_print('Enter tenant url. (ex: https://app.ca.prismacloud.io):', color='blue')
    url = input()
    print()
    new_url = validate_url(url)
    if new_url != url:
        c_print('Adjusted URL:',color='yellow')
        print(new_url)
        print()

    c_print('Enter tenant access key:', color='blue')
    a_key = input()
    print()

    c_print('Enter tenant secret key:', color='blue')
    s_key = input()
    print()
    

    return 'PC-Tenant', a_key, s_key, new_url

#==============================================================================

def build_session_dict(name, a_key, s_key, url):
    session_dict = {
        name: {
            'access_key': a_key,
            'secret_key': s_key,
            'api_url': url
            }
    }
    return session_dict

#==============================================================================

def get_credentials_from_user():
    #Gets the source tenant credentials and ensures that are valid
    credentials = []

    valid = False
    while not valid:
        c_print('Enter credentials for the source tenant. (The tenant the other \'clone\' tenants will replicate)', color='blue')
        print()
        src_name, src_a_key, src_s_key, src_url = get_tenant_credentials()
        
        valid = validate_credentials(src_a_key, src_s_key, src_url)
        if valid == False:
            c_print('FAILED', end=' ', color='red')
            print('Invalid credentails. Please re-enter your credentials')
            print()
        else:
            credentials.append(build_session_dict(src_name, src_a_key, src_s_key, src_url))


    return credentials[0]

def load_yaml(file_name, logger):
    with open(file_name, "r") as file:
        cfg = yaml.load(file, Loader=yaml.BaseLoader)

    credentials = cfg['credentials']
    mode = cfg['mode']
    modes = json.loads(cfg['modes'])
    #Parse cfg for tenant names and create tokens for each tenant
    tenant_sessions = []
    for tenant in credentials:
        tenant_name = ''
        tenant_keys = tenant.keys()
        for name in tenant_keys:
            tenant_name = name     

        a_key = tenant[tenant_name]['access_key']
        s_key = tenant[tenant_name]['secret_key']
        api_url = tenant[tenant_name]['api_url']

        tenant_sessions.append(Session(tenant_name, a_key, s_key, api_url, logger))

    return tenant_sessions, mode, modes

def load_uuid_yaml(file_name, logger):
    with open(file_name, "r") as file:
        cfg = yaml.load(file, Loader=yaml.BaseLoader)

    credentials = cfg['credentials']
    entity_type = cfg['type']
    uuid = cfg['uuid']
    cmp_type = cfg['cmp_type']

    tenant_sessions = []
    for tenant in credentials:
        tenant_name = ''
        tenant_keys = tenant.keys()
        for name in tenant_keys:
            tenant_name = name     

        a_key = tenant[tenant_name]['access_key']
        s_key = tenant[tenant_name]['secret_key']
        api_url = tenant[tenant_name]['api_url']

        tenant_sessions.append(Session(tenant_name, a_key, s_key, api_url, logger))

    return tenant_sessions, entity_type, uuid, cmp_type

def load_config_create_session(file_mode, logger):
    '''
    Reads config.yml and generates a Session object for the tenant

    Returns:
    Tenant Session object
    '''

    if file_mode:
        #Open and load config file
        if not path.exists('tenant_credentials.yml'):
            #Create credentials yml file
            c_print('No credentials file found. Generating...', color='yellow')
            print()
            tenant = get_credentials_from_user()

            with open('tenant_credentials.yml', 'w') as yml_file:
                yaml.dump(tenant, yml_file, default_flow_style=False)

        with open("tenant_credentials.yml", "r") as file:
            cfg = yaml.load(file, Loader=yaml.BaseLoader)

        #Parse cfg for tenant names and create tokens for each tenant

        for tenant in cfg:
            a_key = cfg[tenant]['access_key']
            s_key = cfg[tenant]['secret_key']
            api_url = cfg[tenant]['api_url']

            tenant_session = Session(tenant, a_key, s_key, api_url, logger)

        return tenant_session
    else:
        tenant = get_credentials_from_user()
        for key in tenant:
            name = key

            tenant_session = Session(name, tenant[name]['access_key'], tenant[name]['secret_key'], tenant[name]['api_url'], logger)

        return tenant_session

if __name__ == '__main__':
    validate_url('app.ca.anz.prismacloud.io/home/beans')