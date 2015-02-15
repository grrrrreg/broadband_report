import pycountry
import wolframalpha
import logging
# import wolfram_api_config
import json
# import test_bbreport as test

# this way my wolfram config file is not share with everyone in the git repo
try:
    import wolfram_api_config
    logging.debug('wolfram_api_config successfully loaded')
except ImportError:
    logging.error('your wolfram_api_config python module is missing - contains your API credentials')
    print 'your wolfram_api_config module should contain one hashmap named WOLFRAM_API, structured as below: '
    print json.dumps({'app_name': '<YOUR_API_APP_NAME>', 'app_key': '<YOUR_API_APP_KEY>'}, indent=4)

WOLFRARM_QUERY_BASE = 'Broadband users in '
RESPONSE_POD_TITLE = 'Telecommunications information'
FILTER_LIST = [' million', ' billion', ' people', '% of population', 'world rank', ' estimate', ' Mb/s']


def filter_values(filter_list, filtered_string):
    '''returns True if all of filter_list values are not contained in filtered_string'''
    for item in filter_list:
        if item in filtered_string:
            return False
    return True


def dict_key_from_value(hashmap, value):
    '''only works if 1st argument is a dict and if all values are unique
    the corresponding key is returned when  value is found
    False is returned when ther is no correpsonding key'''
    if not isinstance(hashmap, dict):
        raise TypeError
        logging.error('ERROR: hashmap argument of dict_key_from_value() is not a DICT')
    else:
        if len(hashmap.values()) != len(set(hashmap.values())):
            raise TypeError
            logging.error('values in hashmap argument of dict_key_from_value() are not unique, no 1-to-1 lookup'
                          ' possible')
        else:
            for key in hashmap.keys():
                if hashmap[key].lower() == value.lower():
                    return key
            logging.debug('WARNING: value was not found in argument hashmap, returning FALSE')
            return False


def country_list():
    '''builds and returns a dict with all countries
    has a dependency on the PyCountry module
    returned dict structure: {"<alpha2>:"<country_name>",...}'''
    # return [{country.name: country.alpha2} for country in pycountry.countries]
    return_obj = {}
    for country in pycountry.countries:
        return_obj[country.alpha2] = country.name
    return return_obj


def isvalid_country_alpha2(query, country_list):
    '''tests if a two characters strings corresponds to a valid alpha2 country,
    if it is, returns the (<alpha>, <country_name>) else returns false'''
    if not isinstance(query, basestring):
        raise TypeError
        logging.error('argument of isvalid_country_alpha2() is not a string')
        return False
    else:
        if len(query) != 2:
            logging.debug(' [WARNING] input string is not two characters long')
        else:
            return (query, country_list[query])


def reverse_country(mapping, country):
    '''returns either litteral country name or code depending on which was provided'''
    if not isinstance(mapping, dict):
        raise TypeError
    else:
        if country in mapping.keys():
            return mapping[country]
        else:
            if country in mapping.values():
                return dict_key_from_value(mapping, country)
            else:
                # if value is neither in Keys or Values, return false
                return False


def country_query(country_name, query=False):
    '''executes the actual wolfram API query'''
    # test if the country is in the spawned country list

    wclient = wolframalpha.Client(wolfram_api_config.WOLFRAM_API['api_key'])
    try:
        if country_name:
            response = wclient.query(WOLFRARM_QUERY_BASE + country_name)
        else:
            if query:
                response = wclient.query(query)
            else:
                logging.debug(' [WARNING] inconsistent country_query() parameters')
                return False

        wresponse = []
        string_response = ''
        for pod in response.pods:
            if pod.title == RESPONSE_POD_TITLE:
                string_response = pod.main.text
                response_lines = string_response.split("\n")
                for line in response_lines:
                    curr_split = line.split(' | ')
                    wresponse.append({
                                     'metric': curr_split[0],
                                     'value': curr_split[1]})
                return wresponse
            else:
                logging.debug("EMPTY RESPONSE: wolfram alpha has no data for " + country_name)
    except Exception, e:
        error_msg = e
        logging.error("WOLFRAM CLIENT ERROR: " + str(error_msg))


def country_response_cleanup(response):
    result = []
    for i, metric in enumerate(response):
        result.append({'metric': response[i]['metric'].replace('rate', 'rate Mb/s')})
        tmp_array = metric['value'].split(' (')
        tmp_array = [x.replace(')', '').rstrip() for x in tmp_array]
        for j, item in enumerate(tmp_array):
            # print item
            if ' million' in item:
                # print 'TROUUUVAAYYYYYY'
                if ' million people' in item:
                    # print 'TROUUUVAAYYYYYY BIS REPETITA'
                    result[i]['value'] = int(float(item.replace(' million people', '')) * 1000000)
                else:
                    result[i]['value'] = int(float(item.replace(' million', '')) * 1000000)

            if ' billion' in item:
                if ' billion people' in item:
                    result[i]['value'] = int(float(item.replace(' billion people', '')) * 1000000000)
                else:
                    result[i]['value'] = int(float(item.replace(' billion', '')) * 1000000000)

            if ' people' in item and ' million' not in item and ' billion' not in item:
                result[i]['value'] = int(float(item.replace(' people', '')))

            if '% of population' in item:
                result[i]['percent_of_population'] = float(item.replace('% of population', ''))

            if 'world rank: ' in item:
                rank = item.replace('world rank: ', '')
                rank = rank.replace('st', '')
                rank = rank.replace('nd', '')
                rank = rank.replace('rd', '')
                rank = int(rank.replace('th', ''))
                result[i]['world_rank'] = rank

            if ' Mb/s' in item:
                result[i]['value'] = float(item.replace(' Mb/s', ''))

            if ' estimate' in item:
                result[i]['estimated_metric_age'] = int(item.replace(' estimate', ''))

            if filter_values(FILTER_LIST, item):
                result[i]['value'] = int(item)

    return result


def main():
    '''main loop'''

if __name__ == '__main__':
    main()
