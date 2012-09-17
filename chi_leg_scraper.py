import sqlite3
import urllib
import urllib2
from BeautifulSoup import BeautifulSoup
import re

conn = sqlite3.connect("chicago_legislation.db")
c = conn.cursor()

class ChicagoLegistar :
  def __init__(self, uri) :
    self.data = {
      r'__VIEWSTATE' : r'',
      r'ctl00_RadScriptManager1_HiddenField' : r'', 
      r'ctl00_ContentPlaceHolder1_menuMain_ClientState' : r'',
      r'ctl00_ContentPlaceHolder1_gridMain_ClientState' : r''
      }

    self.headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
      }

    f = urllib2.urlopen(uri)
    self.getStates(f)


  def getStates(self, f) :

    soup= BeautifulSoup(f)

    self.data['__VSTATE'] = soup.fetch('input', {'name' : '__VSTATE'})[0]['value']
    self.data['__EVENTVALIDATION'] = soup.fetch('input', {'name' : '__EVENTVALIDATION'})[0]['value']
  
 

  def searchLegislation(self, search_text, search_fields = None) :
    self.search_args = {
      r'ctl00$ContentPlaceHolder1$txtSearch' : search_text,   # Search text
      r'ctl00_ContentPlaceHolder1_lstYears_ClientState' : '{"value":"This Year"}', # Period to Include
      r'ctl00$ContentPlaceHolder1$lstTypeBasic' : 'All Types',  #types to include
    }

    for field in search_fields:
      if field == 'file number' :
        self.search_args[r'ctl00$ContentPlaceHolder1$chkID'] = 'on'
      elif field == 'legislative text' :
        self.search_args[r'ctl00$ContentPlaceHolder1$chkText'] = 'on'
      elif field == 'attachment' :
        self.search_args[r'ctl00$ContentPlaceHolder1$chkAttachments'] = 'on'
      elif field == 'other' :
        self.search_args[r'ctl00$ContentPlaceHolder1$chkOther'] = 'on'

    

    fields = dict(self.data.items()
                  + self.search_args.items()
                  + [(r'ctl00$ContentPlaceHolder1$btnSearch',
                      'Search Legislation')]
                  )

    # these have to be encoded    

    encoded_fields = urllib.urlencode(fields)
    
    req = urllib2.Request(uri, encoded_fields, self.headers)
    f = urllib2.urlopen(req).read()  #that's the actual call to the http site.

    result_page_urls = self.resultsUrls(f)

    return f, result_page_urls

  def resultsUrls(self, f) :

    soup = BeautifulSoup(f)
    self.getStates(f)


    result_page_urls = []

    for match in soup.fetch('a', {'href':re.compile('ctl02\$ctl00')}) :
      event_target = match['href'].split("'")[1]

      result_page_args =  {
        r'__EVENTTARGET' : event_target,
        r'__EVENTARGUMENT' : ''
      }

      fields = dict(self.data.items()
                    + self.search_args.items()
                    + result_page_args.items()
                    )
      # these have to be encoded    
      encoded_fields = urllib.urlencode(fields)

      req = urllib2.Request(uri, encoded_fields, self.headers)      

      result_page_urls.append(req)

    return result_page_urls

  def parseSearchResults(self, f) :
    """Take a page of search results and return a sequence of data
    of tuples about the legislation, of the form

    ('Document ID', 'Document URL', 'Type', 'Status', 'Introduction Date'
     'Passed Date', 'Main Sponsor', 'Title')
    """
    soup= BeautifulSoup(f)
    
    legislation_rows = soup.fetch('tr', {'id':re.compile('ctl00_ContentPlaceHolder1_gridMain_ctl00__')})
    print "found some legislation!"
    print len(legislation_rows)
    
    
    legislation_list = []
    for row in legislation_rows :
      legislation = []
      for field in row.fetch("td") :
        legislation.append(field.text)
      legislation.append(row.fetch("a")[0]['href'])
      legislation_list.append(legislation)
      
    return legislation_list


  def parseLegislationDetail(self, url) :
    """Take a legislation detail page and return a dictionary of
    the different data appearing on the page

    Example URL: http://chicago.legistar.com/LegislationDetail.aspx?ID=1050678&GUID=14361244-D12A-467F-B93D-E244CB281466&Options=ID|Text|&Search=zoning
    """
    f = urllib2.urlopen(url)
    soup = BeautifulSoup(f)
    detail_div = soup.fetch('div', {'id' : 'ctl00_ContentPlaceHolder1_pageDetails'})
    keys = []
    values = []
    i = 0
    for cell in  detail_div[0].fetch('td')[0:25] :
      if i % 2 :
          values.append(cell.text)
      else :
        keys.append(cell.text)
      i += 1

    details = dict(zip(keys, values))

    history_row = soup.fetch('tr', {'id' : re.compile('ctl00_ContentPlaceHolder1_gridLegislation_ctl00')})

    history_keys = ["date", "journal_page", "action_by", "status", "results", "votes", "meeting_details"]

    history = []

    for row in history_row :
      values = []
      for cell in row.fetch('td') :
        values.append(cell.text)
      history.append(dict(zip(history_keys, values)))

    print details
    print history
      



#if __name__ == '__main__' :
if False :
  uri = 'http://chicago.legistar.com/Legislation.aspx'
  scraper = ChicagoLegistar(uri)
  # First page of results
  f1, results = scraper.searchLegislation('zoning', ['legislative text'])
  
  legislation_list = scraper.parseSearchResults(f1)
  
  for result in results[1:] :
    # iterate through pages of results
    f = urllib2.urlopen(result)
    legislation_list.extend(scraper.parseSearchResults(f))
   
  print legislation_list  
  print 'we gots the legislations!'
  print len(legislation_list)

  # try:
  #     fout = open('tmp.htm', 'w')
  #   except:
  #     print('Could not open output file\n')
  # 
  #   fout.writelines(f2.readlines())
  #   fout.close()
  
  
  [legislation.pop(4) for legislation in legislation_list]
  
  c.executemany('INSERT OR IGNORE INTO legislation '
                '(id, type, status, intro_date, main_sponsor, title, url) '
                'VALUES '
                '(?, ?, ?, ?, ?, ?, ?)',
                legislation_list)

  conn.commit()

if True:
    uri = 'http://chicago.legistar.com/Legislation.aspx'
    scraper = ChicagoLegistar(uri)
    leg_page = "http://chicago.legistar.com/LegislationDetail.aspx?ID=1050678&GUID=14361244-D12A-467F-B93D-E244CB281466"
    
    scraper.parseLegislationDetail(leg_page) 

c.close()


