
import re
from collections import OrderedDict
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from urllib.error import URLError
from bs4 import BeautifulSoup  # parsing
from datasketch import MinHash, MinHashLSH

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

#
fingerprintDict = {}
def extract_shingles(content, k=5):
    shingles = set()
    words = content.split()  # Split content into words
    for i in range(len(words) - k + 1):
        shingle = ' '.join(words[i:i+k])  # Form shingles
        shingles.add(shingle)
    return shingles

def compute_minhash(shingles, num_perm=128):
    minhash = MinHash(num_perm=num_perm)
    for shingle in shingles:
        minhash.update(shingle.encode('utf-8'))
    return minhash

def check_similarity(content, threshold=0.8):
    shingles = extract_shingles(content)
    minhash = compute_minhash(shingles)
    
    for _, storedHash in fingerprintDict.items():
        similarity = minhash.jaccard(storedHash)
        if similarity >= threshold:
            return True
    
    return False


def scraper(url, resp):
    try:
        if resp.status == 200:
            links = extract_next_links(url, resp)
            return [link for link in links if is_valid(link)]
        else:
            return []
    except:
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
    if resp.status >= 400 or resp.status == 204:
        return list()
    # PART 2: PARSE
    try:
        beautSoup = BeautifulSoup(resp.raw_response.content, "html5lib")
    except:
        return list()
    
    try:
        content = resp.raw_response.content.decode('utf-8')
    except UnicodeDecodeError:
        content = resp.raw_response.content.decode('utf-8', 'ignore')  # Ignore problematic characters

    if check_similarity(content):
        return  # Move on to the next webpage without returning any links

    fingerprintDict[url] = compute_minhash(extract_shingles(content))  # Store MinHash signature for future comparisons

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
        if resp.status >= 400 or resp.status == 204:
            continue
        if is_valid(absLink):
            if any(canonicalLink in absLink for canonicalLink in canonical):
                continue
            links.add(absLink)

    # global unique_urls, subdomain_page_counts
    # with open("visited_urls.txt", "a") as f:  # Open the file in append mode
    #     for link in links:
    #         # Add to unique_urls set
    #         unique_urls.add(link)

    #         # Subdomain counting for ics.uci.edu
    #         parsed_url = urlparse(link)
    #         domain = parsed_url.netloc
    #         valid_domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]
    #         if any(domain.endswith(valid_domain) for valid_domain in valid_domains):
    #             if domain not in subdomain_page_counts:
    #                 subdomain_page_counts[domain] = set()
    #             subdomain_page_counts[domain].add(link)

    #         # Log the link to the output file (if unique)
    #         if link in unique_urls:
    #             f.write(link + "\n")
        

   #DO NOT CHANGE THIS CODE! THIS IS NEEDED FOR PROPER LEN COUNT FOR THE COMPARISON BELOW. 
    #PLS DO NOT CHANGE IT. TY.
    bodyText = beautSoup.find('body')
    try:
        rawText = bodyText.get_text()
        rawText = re.findall(r"\b[\w']+\b", rawText) #this is for checking high textual or not
    except AttributeError:
        return list()


    # Check content length and token length for each link after they've been added to the set
    for link in list(links):
        tooLargeFile = 10000000  # Too large for email, too large for web crawler
        tooLittleText = 250
        contentLenBytes = len(resp.raw_response.content) 
        tokenizeLen = len(rawText)
        if contentLenBytes > tooLargeFile or tokenizeLen < tooLittleText:
            links.remove(link)


    # # Tokenizer adapted from Jacob's Assignment 1:

    # # List of Tokens
    # tokenizePage = []

    # # Token to be added
    # current_token = ""

    # # For each character in the body text of the page
    # for character in rawText:
    #     # Check if character is alphanumeric
    #     if character.isalnum() & character.isascii():
    #         # Append current character to token to be added
    #         current_token += character
    #     else:
    #         # Check if current token being created is not empty
    #         if current_token != "":
    #             # Add token to list of tokens
    #             tokenizePage.append(current_token.lower())
    #             # Clear current token
    #             current_token = ""

    # # Add last token to list (if there is one)
    # if current_token != "":
    #     tokenizePage.append(current_token.lower())

    # global longest
    # if len(tokenizePage) > longest[1]:
    #     longest = (resp.url, len(tokenizePage))

    # # For each token in the supplied list (on average, checked in constant time)
    #     for token in tokenizePage:
    #         # If the token's key-value pair in the dictionary has not been created yet
    #         # (on average, checked in constant time)
    #         if token not in allFrequencies:
    #             # Create a key-value pair for the token
    #             allFrequencies[token] = 1
    #         else:
    #             # Increase the value of the token's key-value pair by 1
    #             allFrequencies[token] += 1

    # global top50Words
    # top50Words = (sorted(allFrequencies.items(), key=lambda item: (-item[1], item[0])))[:50]

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

        if(".php" in ext.lower() or ".img" in ext.lower() or ".mpg" in ext.lower() or ".gif" in ext.lower() or ".mp4" in ext.lower() or ".mov" in ext.lower() or ".avi" in ext.lower() or ".flv" in ext.lower()):#dynamic files or non textual files
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