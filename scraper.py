import re
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup #parsing

def scraper(url, resp):
    links = extract_next_links(url, resp)
    if links:
        return [link for link in links if is_valid(link)]
    else:
        return []


def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page! 
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    #CHECK ALL ERRORS AND EXCEPTIONS WITHIN EXTRACT_NEXT_LINKS ARE COVERED
    if (resp.status >= 400 or resp.status == 204):
        return list()

    beautSoup = BeautifulSoup(resp.raw_response.content, "html.parser")
    links = set()
    canonical = set()
    #NEXT STEP: FIGURE OUT HOW TO GRAB TEXT AND PARSE WITH TOKENIZER: https://www.educative.io/answers/how-to-use-gettext-in-beautiful-soup
    bodyText = beautSoup.find('body')
    tokenizePage = bodyText.get_text()
    tokenizePage = re.findall(r'\b\w+\b', tokenizePage) #this is for checking high textual or not
    #call tokenizer here: tokenizer should alr store everything so will wait for function to be done

    #CHECK IF HIGH TEXTUAL CONTENT
    #CHECK IF TOO LARGE FILE WITH LOW TEXTUAL CONTENT
    tooLargeFile = 10000000 #too large for email, too large for web crawler 
    tooLittleText = 50
    contentLenBytes = len(resp.raw_response.content)
    tokenizeLen = len(tokenizePage)

    if contentLenBytes > tooLargeFile:
        if tokenizeLen < tooLittleText:
            return list()

    #checks for canonical to reduce duplicates
    for i in beautSoup.find_all("link", rel = "canonical"):
        canonicalURL = i.get("href")
        if canonicalURL:
            canonical.add(canonicalURL)


    #find hyperlinks to crawl: https://www.scrapingbee.com/webscraping-questions/beautifulsoup/how-to-find-all-links-using-beautifulsoup-and-python/
    for i in beautSoup.find_all("a"):
        link = i.get("href")
        absLink = urljoin(url, link)
        if is_valid(absLink):
            if url in canonical:
                continue
            links.add(absLink)

    return list(links)


def is_valid(url):


    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.

    try:
        parsed = urlparse(url)
        #maybe add a dot in front of each one IF he says anything about futurehealth.ics not being ok
        if not re.match(r'^(\w*.)(ics\.uci\.edu|cs\.uci\.edu|stat\.uci\.edu|informatics\.uci\.edu)$', parsed.netloc):
            return False
        if parsed.scheme not in set(["http", "https"]):
            return False
        domain = parsed.netloc
        return not re.match(
            r".*.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

        try:
            robot_parser = RobotFileParser()
            robot_parser.set_url(domain + "/robots.txt")
            robot_parser.read()
            if(robot_parser.can_fetch("UCICrawler",url)):
                return True
            else:
                return False
        except URLError:#would I return false
            return False


    except TypeError:
        print ("TypeError for ", parsed)
        raise