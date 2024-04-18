import re
from urllib.parse import urlparse, urljoin

from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup #parsing


cache = {}

def scraper(url, resp):
    links = extract_next_links(url, resp)
    if links != None:
        return [link for link in links if is_valid(link)]
    else:
        return []

def extract_next_links(url, resp): #maybe restart cache here?
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page! 
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    #QUESTION: worker.log and what the status tther means
    # how to understand
    if resp.status >= 400 or resp.status == 204:
        return list()
        
    #basic basic crawler
    beautSoup = BeautifulSoup(resp.raw_response.content, "html.parser")
    links = set()

    #find hyperlinks: https://www.scrapingbee.com/webscraping-questions/beautifulsoup/how-to-find-all-links-using-beautifulsoup-and-python/
    for i in beautSoup.find_all("a"):
        link = i.get("href")
        absLink = urljoin(url, link)
        if is_valid(absLink):#consider checking for duplciates here, lowercase link and then check in list, uRLS are not case sensitive but using find to find them iwll be 
            links.add(absLink)
    return list(links)

def is_valid(url):


    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.

    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False

        if not re.match(r'^(\w*.)(ics.uci.edu|cs.uci.edu|stat.uci.edu|informatics.uci.edu)$', parsed.netloc):#filter out domains not valid for this assignment
            return False

        if "/calendar?date=" in url:#calendars have traps
            return False

        if "/?s=" in url:#if search page with will bring up a large amount of repeated information, trap
            return False#but im not sure if i would be filtering out content that may be useful or unique to be found only through search
        
        domain = parsed.netloc
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

        try:
            if(domain not in cache):#if not already in cache, process, if not dont send another request to be polite
                robot_parser = RobotFileParser()
                robot_parser.set_url(domain + "/robots.txt")#for the purposes of Assignment 2, since we are crawling uci.edu domains, we know that this is how their robot files are found and we dont need other methods
                robot_parser.read()
            else:
                robot_parser = cache[domain]
            
            if(robot_parser.can_fetch("UCICrawler",url)):
                return True
            else:
                return False
        except URLError:#would I return false
            return False

            
        

    except TypeError:
        print ("TypeError for ", parsed)
        raise