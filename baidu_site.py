from recon.core.module import BaseModule
import urllib
import re
import time
import random

class Module(BaseModule):

    meta = {
        'name': 'Baidu Hostname Enumerator',
        'author': 'Tim Tomes (@LaNMaSteR53)',
        'description': 'Harvests hosts from Baidu.com by using the \'site\' search operator. Updates the \'hosts\' table with the results.',
        'query': 'SELECT DISTINCT domain FROM domains WHERE domain IS NOT NULL ORDER BY domain'
    }

    def module_run(self, domains):
        base_url = 'http://www.baidu.com/s'
        for domain in domains:
            self.heading(domain, level=0)
            base_query = 'site:(%s)' % domain
            pattern = '(?<=<div class="f13"><a target="_blank" href=")\S*(?=")'
            subs = []
            # control variables
            new = True
            page = 0
            nr = 10
            # execute search engine queries and scrape results storing subdomains in a list
            # loop until no new subdomains are found
            while new == True:
                content = None
                query = ''
                # build query based on results of previous results
                for sub in subs:
                    query += ' -site:(%s.%s)' % (sub, domain)
                full_query = base_query + query
                url = '%s?pn=%d&wd=%s' % (base_url, (page*nr), urllib.quote_plus(full_query))
                # baidu errors out at > 2054 characters not including the protocol
                if len(url) > 2061: 
                    url = url[:2061]

                self.verbose('URL: %s' % (url))
                # send query to search engine
                resp = self.request(url, redirect=False)
                if resp.status_code != 200:
                    self.alert('Baidu has encountered an error. Please submit an issue for debugging.')
                    break
                content = resp.text
                sites = re.findall(pattern, content)
                # create a unique list
                sites = list(set(sites))
                new = False
                # add subdomain to list if not already exists
                p = '(?<=replace\(")\S*(?=")'
                for site in sites:
                    r = self.request(site, redirect=False)
                    tmp = re.search(p,r.text)
                    tmp_site = tmp.group(0).split('/')[2].split('.' + domain)[0] 
                    
                    if tmp_site not in subs and tmp_site != domain:                    
                        subs.append(tmp_site)
                        new = True
                        host = '%s.%s' % (tmp_site, domain)
                        self.output('%s' % (host))
                        self.add_hosts(host)
                if not new:
                    # exit if all subdomains have been found
                    if u'>\u4e0b\u4e00\u9875&gt;<' not in content or page > 10:
                        break
                    else:
                        page += 1
                        self.verbose('No New Subdomains Found on the Current Page. Jumping to Result %d.' % ((page*nr)+1))
                        new = True
                # sleep script to avoid lock-out
                self.verbose('Sleeping to avoid lockout...')
                time.sleep(random.randint(5,15))
