import re
from collections import OrderedDict
from urllib.parse import urlparse, urljoin

from urllib.robotparser import RobotFileParser

from urllib.error import URLError

from bs4 import BeautifulSoup  # parsing

cache = {}

#####
unique_urls = set()  # To store unique URLs
subdomain_page_counts = {}  # To store unique pages per subdomain in ics.uci.edu
#####

stopWords = ("a","about","above","after","again","against","all","am","an","and","any",
             "are","aren't","as","at","be","because","been","before","being","below",
             "between","both","but","by","can't","cannot","could","couldn't","did",
             "didn't","do","does","doesn't","doing","don't","down","during","each",
             "few","for","from","further","had","hadn't","has","hasn't","have",
             "haven't","having","he","he'd","he'll","he's","her","here","here's",
             "hers","herself","him","himself","his","how","how's","i","i'd","i'll",
             "i'm","i've","if","in","into","is","isn't","it","it's","its","itself",
             "let's","me","more","most","mustn't","my","myself","no","nor","not",
             "of","off","on","once","only","or","other","ought","our","ours",
             "ourselves","out","over","own","same","shan't","she","she'd","she'll",
             "she's","should","shouldn't","so","some","such","than","that","that's",
             "the","their","theirs","them","themselves","then","there","there's",
             "these","they","they'd","they'll","they're","they've","this","those",
             "through","to","too","under","until","up","very","was","wasn't","we",
             "we'd","we'll","we're","we've","were","weren't","what","what's","when",
             "when's","where","where's","which","while","who","who's","whom","why",
             "why's","with","won't","would","wouldn't","you","you'd","you'll","you're",
             "you've","your","yours","yourself","yourselves")
longest = ("", 0)
allFrequencies = dict()
top50Words = OrderedDict()


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

    # PART 1: CRAWL POLITELY
    if resp.status >= 400 or resp.status == 204 or resp.status == 404 or resp.status == 601 or resp.status == 600:
        return list()

    # PART 2: PARSE
    try:
        beautSoup = BeautifulSoup(resp.raw_response.content, "html5lib")
    except:
        return list()

    canonical = set()

    # checks for canonical to reduce duplicates; will change after videos on near similarity and perfect similarity
    for i in beautSoup.find_all("link", rel="canonical"):
        canonicalURL = i.get("href")
        if canonicalURL:
            canonical.add(canonicalURL)

    links = set()

    # find hyperlinks to crawl:
    # https://www.scrapingbee.com/webscraping-questions/beautifulsoup/how-to-find-all-links-using-beautifulsoup-and-python/
    # also, this finds all links
    for i in beautSoup.find_all("a"):
        link = i.get("href")
        absLink = urljoin(url, link)
        absLink = absLink.split("#")[0]  # normalizing the link
        if is_valid(absLink):
            if any(canonicalLink in absLink for canonicalLink in canonical):
                continue
            links.add(absLink)

    global unique_urls, subdomain_page_counts
    with open("visited_urls.txt", "a") as f:  # Open the file in append mode
        for link in links:
            # Add to unique_urls set
            unique_urls.add(link)

            # Subdomain counting for ics.uci.edu
            parsed_url = urlparse(link)
            domain = parsed_url.netloc
            valid_domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]
            if any(domain.endswith(valid_domain) for valid_domain in valid_domains):
                if domain not in subdomain_page_counts:
                    subdomain_page_counts[domain] = set()
                subdomain_page_counts[domain].add(link)

            # Log the link to the output file (if unique)
            if link in unique_urls:
                f.write(link + "\n")
        

    # NEXT STEP: FIGURE OUT HOW TO GRAB TEXT AND PARSE WITH TOKENIZER: https://www.educative.io/answers/how-to-use-gettext-in-beautiful-soup
    bodyText = beautSoup.find('body')
    try:
        rawText = bodyText.getText()
    except AttributeError:
        return list()

    # Check content length and token length for each link after they've been added to the set
    for link in list(links):
        tooLargeFile = 10000000  # Too large for email, too large for web crawler
        tooLittleText = 250
        contentLenBytes = len(resp.raw_response.content)
        rawTextLen = len(rawText)
        if contentLenBytes > tooLargeFile or rawTextLen < tooLittleText:
            links.remove(link)

    tokenizePage = [text for text in rawText.split(' ') if text.isalnum() and text.isascii() and text not in stopWords]
    global longest
    if len(tokenizePage) > longest[1]:
        longest = (resp.url, len(tokenizePage))

    # For each token in the supplied list (on average, checked in constant time)
        for token in tokenizePage:
            # If the token's key-value pair in the dictionary has not been created yet
            # (on average, checked in constant time)
            if token not in allFrequencies:
                # Create a key-value pair for the token
                allFrequencies[token] = 1
            else:
                # Increase the value of the token's key-value pair by 1
                allFrequencies[token] += 1

    global top50Words
    top50Words = (sorted(allFrequencies.items(), key=lambda item: (-item[1], item[0])))[:50]

    # albert code here
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

        base_url = parsed.scheme + "://" + parsed.netloc + parsed.path
        if parsed.fragment:
            # If there's a fragment, consider only the base URL without the fragment
            return False

        if "/calendar?date=" in url:#calendars have traps
            return False

        if "/?s=" in url:#if search page with will bring up a large amount of repeated information, trap
            return False#but im not sure if i would be filtering out content that may be useful or unique to be found only through search

        url_path = parsed.path
        if '.' in url_path:
            ext = url_path[url_path.rfind('.'):]  # This gets the substring from the last period to the end.
        else:
            ext = ''  # No extension found

        if(".php" in ext.lower()):#dynamic files
            return False

        if(".img" in ext.lower()):#non textual
            return False
    
    
        try:
            if((parsed.netloc) not in cache):#if not already in cache, process, if not dont send another request to be polite, parsed.netloc is domain
                robot_parser = RobotFileParser()
                robot_parser.set_url(parsed.scheme + "://" +(parsed.netloc) + "/robots.txt")#for the purposes of Assignment 2, since we are crawling uci.edu domains, we know that this is how their robot files are found and we dont need other methods
                robot_parser.read()
                cache[parsed.netloc] = robot_parser
            else:
                robot_parser = cache[parsed.netloc]
            
            if(robot_parser.can_fetch("UCICrawler",url)):
                return not re.match(
                    r".*\.(css|js|bmp|gif|jpe?g|ico"
                    + r"|png|tiff?|mid|mp2|mp3|mp4"
                    + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
                    + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                    + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                    + r"|epub|dll|cnf|tgz|sha1"
                    + r"|thmx|mso|arff|rtf|jar|csv"
                    + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

               #return True
            else:
                return False
        except URLError:#would I return false
            return False

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def report_stats():
    global unique_urls, subdomain_page_counts, top50Words

    print(f"Total unique pages found: {len(unique_urls)}")
    print(f"Longest page: {longest[0]} with {longest[1]} words.")
    print(f"Top 50 common words: {top50Words}")
    
    print("Subdomains within ics.uci.edu and their unique page counts:")
    sorted_subdomains = sorted(subdomain_page_counts.items())  # Sorts by the subdomain (the dict key)
    for domain, pages in sorted_subdomains:
        if ".ics.uci.edu" in domain:  # Ensure we only report for ics.uci.edu subdomains
            print(f"{domain}: {len(pages)} unique pages")