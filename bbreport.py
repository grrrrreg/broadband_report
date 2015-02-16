import pycountry
import wolframalpha
import logging
import json
import csv
# import test_bbreport as test

# Dynamic loading of the wolfram config
# this way my wolfram config file is not shared with everyone...
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


def country_query(country_name, query=False, debug=False):
    '''executes the actual wolfram API query
    the returned result looks like test_bbreport.FRANCE[\'dirty\']
    I\'m assuming I don't know what sub-fields the Wolfram API will yield, the country_response_cleanup() does this'''

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
                if debug:
                    return response_lines
                else:
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
    ''' takes a contry_query() object return that looks like test_bbreport.FRANCE[\'dirty\']
    and turns it into an object that looks like test_bbreport.FRANCE[\'clean\']
    you can\'t know in advance which fields Wolfram API will generate in the string, if new ones pop-up, this
    fuction will need to be amended accordingly'''

    result = []
    for i, metric in enumerate(response):
        result.append({'metric': response[i]['metric'].replace('rate', 'rate Mb/s')})
        tmp_array = metric['value'].split(' (')
        tmp_array = [x.replace(')', '').rstrip() for x in tmp_array]
        for j, item in enumerate(tmp_array):
            # print item
            if ' million' in item:
                if ' million people' in item:
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


def mkreport(countries):
    '''builds a json w/ multiple country broadband statistics in it
    country argument is an array, contains alpha2 strings.
    "countries" argument needs to be a list of valid alpha2 codes
    --> returned report is already ran through country_response_cleanup()
    --> returned report can then be run through flatten_report() or mk_csv_from_report()'''

    official_countries = country_list()

    if not isinstance(countries, list):
        logging.error('countries argument in mkreport() is not an array of alpha2 countries')
        raise TypeError
    else:
        for elt in countries:
            if elt not in official_countries.keys():
                logging.error(elt.upper() + ' - INVALID Alpha2 Country')
            else:
                report = {}
                for country in countries:
                    country_name = official_countries[country]
                    curr_report = country_response_cleanup(country_query(country_name))
                    report['country_name'] = curr_report
                return report


def mk_columns_from_report(report):
    ''' dynamically computes the 1st row for display_report() as a header, depending on the amount of fields that
    mkreport() - dynamically detects the resulting union of columns from each country report in the report argument'''

    header = ['country', 'country_alpha2']
    header_filter = ['metric', 'value']

    for country in report:
        for metrics in report[country]:
            curr_metric = metrics['metric']
            if curr_metric not in header:
                header.append(curr_metric)
                for field in metrics:
                    if field not in header_filter:
                        header.append(field)
    return header


def flatten_report(report):
    '''uses a mkreport() output and displays it in a human friendly way
    tries to figure out what fields to display dynamically from the report argument
    --> calls mk_columns_from_report() to build header as 1st entry of return'''

    header_filter = ['metric', 'value']

    # make header
    official_countries = country_list()
    table = []
    table.append(mk_columns_from_report(report))
    for country in report:
        curr_record = []
        curr_record.append(country)
        for alpha2 in official_countries:
            if official_countries[alpha2] == country:
                curr_record.append(alpha2)
        for metric in report[country]:
            curr_record.append(metric['value'])
            for key in metric:
                if key not in header_filter:
                    curr_record.append(metric[key])
        table.append(curr_record)
    return table


def mk_csv_from_report(report, file_name):
    ''' writes a CSV file from a report, openable in XLS
    --> "report" argument needs to be in the format returned by mkreport()'''

    f = open(file_name, 'wt')
    try:
        writer = csv.writer(f)
        for line in flatten_report(report):
            writer.writerow(line)
    finally:
        f.close()


def main():
    '''main loop'''

if __name__ == '__main__':
    main()
