import re
from collections import Counter, OrderedDict
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup  # parsing
from bs4.element import Comment
from simhash import Simhash

cache = {}

#####
unique_urls = set()  # To store unique URLs
subdomain_page_counts = {}  # To store unique pages per subdomain in ics.uci.edu
#####

# Stopwords from https://www.ranks.nl/stopwords
stopWords = ("a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any",
             "are", "aren't", "as", "at", "be", "because", "been", "before", "being", "below",
             "between", "both", "but", "by", "can't", "cannot", "could", "couldn't", "did",
             "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each",
             "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
             "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's",
             "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
             "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
             "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not",
             "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
             "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll",
             "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
             "the", "their", "theirs", "them", "themselves", "then", "there", "there's",
             "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
             "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
             "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when",
             "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why",
             "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
             "you've", "your", "yours", "yourself", "yourselves")

longest = ("", 0)  # To keep track of the longest page
allFrequencies = Counter()  # Frequencies of all words scraped
top50Words = OrderedDict()  # Top 50 words (with filtering) scraped
links = set()
fingerPrint = list()


def compute_and_check_similarity(content, threshold=3):
    try:
        simhash = Simhash(content)
        for i in fingerPrint:
            # Calculate Hamming distance between the current Simhash and stored hashes
            distance = simhash.distance(i)
            if distance < threshold:
                return True

        return False

    except Exception as ex:
        print("An exception occurred during scraping:", ex)
        return False


def write_unique_urls_to_file():
    global links
    with open("visited_urls.txt", "w") as f:  # Open the file in append mode
        for link in links:
            # Subdomain counting for ics.uci.edu
            parsed_url = urlparse(link)
            domain = parsed_url.netloc
            valid_domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]
            if any(domain.endswith(valid_domain) for valid_domain in valid_domains):
                if domain not in subdomain_page_counts:
                    subdomain_page_counts[domain] = set()
                subdomain_page_counts[domain].add(link)

            # Log the link to the output file (if unique)
            if link not in unique_urls:
                f.write(link + "\n")
                unique_urls.add(link)


def update_subdomain_page_counts(url):
    # Extract hostname from the URL
    hostname = urlparse(url).hostname

    # Ensure it belongs to ics.uci.edu subdomains
    if ".ics.uci.edu" in hostname:
        subdomain = hostname

        # Initialize the subdomain set in the dictionary if not already present
        if subdomain not in subdomain_page_counts:
            subdomain_page_counts[subdomain] = set()

        # Add the normalized URL to the set associated with the subdomain
        subdomain_page_counts[subdomain].add(url)


# Adapted from: https://stackoverflow.com/questions/1936466/how-to-scrape-only-visible-webpage-text-with-beautifulsoup
# Used to only extract visible text from the webpage
def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    return True


def tokenize_webpage(content):
    word_list = []
    word = ""

    # Adapted from: https://stackoverflow.com/questions/1936466/how-to-scrape-only-visible-webpage-text-with-beautifulsoup
    # Extracting visible text from the webpage
    try:
        beautSoup = BeautifulSoup(content, "html5lib")
        texts = beautSoup.findAll(string=True)
        visible_texts = filter(tag_visible, texts)
        texts = u" ".join(t.strip() for t in visible_texts)
    except:
        texts = ""

    # Assignment 1 tokenization
    for ch in texts:
        if (47 < ord(ch) < 58) or (64 < ord(ch) < 91) or (
                96 < ord(ch) < 123):  # Simple check for alphanumeric characters
            word += ch
        else:
            if word:
                word_list.append(word.lower())  # Convert to lower case to ignore case-sensitivity
                word = ""  # Reset for next word

    if word:  # if there's a word left at the end, add it to the list
        word_list.append(word.lower())

    return [word for word in word_list if word]


def scraper(url, resp):
    try:
        pageTokens = []  # Initialize pageTokens as a local variable
        pageSimHash = 0
        if resp.status == 200:
            pageTokens = tokenize_webpage(resp.raw_response.content)
            pageSimHash = Simhash(' '.join(pageTokens))

            if compute_and_check_similarity(pageSimHash):
                return []
            else:
                fingerPrint.append(pageSimHash)  # Store the Simhash for future comparisons

            try:
                beautSoup = BeautifulSoup(resp.raw_response.content, "html5lib")
            except Exception as e:
                print("Unable to create Beautiful Soup.")
                return

            bodyText = beautSoup.find('body')
            try:
                rawText = bodyText.get_text()
                rawText = re.findall(r"\b[\w']+\b", rawText)  # this is for checking high textual or not
            except AttributeError:
                print("Unable to make rawtext.")
                return []

            tooLargeFile = 10000000  # Too large for email, too large for web crawler
            tooLittleText = 250
            contentLenBytes = len(resp.raw_response.content)
            tokenizeLen = len(rawText)
            if contentLenBytes > tooLargeFile or tokenizeLen < tooLittleText:
                return []

            unique_urls.add(url)  # what we ended up actually crawling

            ###ADDED FOR REPORT###
            update_subdomain_page_counts(url)

            global allFrequencies, longest

            # Tokenize the webpage
            pageTokens = tokenize_webpage(resp.raw_response.content)
            pageWordCount = len(pageTokens)

            # Update global longest page if this page has more words
            if pageWordCount > longest[1]:
                longest = (url, pageWordCount)

            # Update global word frequencies
            allFrequencies.update(pageToken for pageToken in pageTokens if pageToken not in stopWords)

            ###ADDED FOR REPORT###

            with open("forMe.txt", "a") as f:  # Open the file in append mode
                # Log the link to the output file (if unique)
                # if link not in unique_urls:
                f.write(url + "\n")
            links = extract_next_links(url, resp)
            return [link for link in links if is_valid(link)]
        else:
            return []
    except HTTPError:
        print("HTTPError")
    except ConnectionError:
        print("ConnectionError")
    except Exception as e:
        print("Exception ", e)


def extract_next_links(url, resp):
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    try:
        if not resp.raw_response:
            return list()

        try:
            beautSoup = BeautifulSoup(resp.raw_response.content, "html5lib")
        except Exception as e:
            print("Unable to create Beautiful Soup.")
            return

        canonical = set()

        for i in beautSoup.find_all("link", rel="canonical"):
            canonicalURL = i.get("href")
            if canonicalURL:
                canonical.add(canonicalURL)

        for i in beautSoup.find_all("a"):
            link = i.get("href")
            if link:
                absLink = urljoin(url, link)
                absLink = absLink.split("#")[0]  # Remove fragment identifiers
                if is_valid(absLink):
                    if any(canonicalLink in absLink for canonicalLink in canonical):
                        continue
                    links.add(absLink)
    except HTTPError:
        print("HTTPError")
    except ConnectionError:
        print("ConnectionError")
    except Exception as e:
        print("Exception ", e)

    return list(links)


def is_valid(url):
    # Decide whether to crawl this url or not.
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.

    try:
        parsed = urlparse(url)

        if parsed.scheme not in set(["http", "https"]):
            return False

        if not re.match(r'^(\w*.)(ics.uci.edu|cs.uci.edu|stat.uci.edu|informatics.uci.edu)$',
                        parsed.netloc):  # filter out domains not valid for this assignment
            return False

        base_url = parsed.scheme + "://" + parsed.netloc + parsed.path
        if parsed.fragment:
            # If there's a fragment, consider only the base URL without the fragment
            return False

        if "/calendar" in url:  # calendars have traps
            return False

        if "/?s=" in url:  # if search page with will bring up a large amount of repeated information, trap
            return False

        if re.search(
                "(\?share|/login|/signin|/auth|/account|/secure|/admin|\?attachment|&share|&ical|\?ical|/theme|/themes|/datasets.php)",
                url) is not None:
            return False

        url_path = parsed.path
        if '.' in url_path:
            ext = url_path[url_path.rfind('.'):]  # This gets the substring from the last period to the end.
        else:
            ext = ''  # No extension found

        if (
                ".img" in ext.lower() or ".mpg" in ext.lower() or ".gif" in ext.lower() or ".mov" in ext.lower() or ".flv" in ext.lower() or ".ical" in ext.lower() or ".ics" in ext.lower() or ".js" in ext.lower()):  # dynamic files or non textual files
            return False

        try:
            if ((
            parsed.netloc) not in cache):  # if not already in cache, process, if not dont send another request to be polite, parsed.netloc is domain
                robot_parser = RobotFileParser()
                robot_parser.set_url(parsed.scheme + "://" + (
                    parsed.netloc) + "/robots.txt")  # for the purposes of Assignment 2, since we are crawling uci.edu domains, we know that this is how their robot files are found and we dont need other methods
                robot_parser.read()
                cache[parsed.netloc] = robot_parser
            else:
                robot_parser = cache[parsed.netloc]

            if (robot_parser.can_fetch("UCICrawler", url)):

                if (".php" == parsed.path.lower()):
                    query = str(url).split(".php")
                    if "/" in query[1] or len(query) > 2:
                        return False
                    if str(url).count("//") > 1:
                        return False

                return not re.match(
                    r".*\.(css|js|bmp|gif|jpe?g|ico"
                    + r"|png|tiff?|mid|mp2|mp3|mp4"
                    + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
                    + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                    + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                    + r"|epub|dll|cnf|tgz|sha1"
                    + r"|thmx|mso|arff|rtf|jar|csv"
                    + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

            # return True
            else:
                return False
        except URLError:  # return false
            return False

    except TypeError:
        print("TypeError for ", parsed)
        raise
    except HTTPError:
        print("HTTPError")
    except ConnectionError:
        print("ConnectionError")
    except Exception as e:
        print("Exception ", e)


def report_stats():
    global unique_urls, subdomain_page_counts, longest, allFrequencies

    # Open a file to write the statistics
    with open('report.txt', 'w') as report_file:
        report_file.write(f"Total unique pages found: {len(unique_urls)}\n")
        report_file.write(f"Longest page: {longest[0]}\n")

        # Write the most common words excluding the stop words, sorted by frequency
        most_common_words = [word for word in allFrequencies.most_common(50)]

        report_file.write(f"{most_common_words}\n")  # Write the top 50 words after filtering

        report_file.write("Subdomains within ics.uci.edu and their unique page counts:\n")
        sorted_subdomains = sorted(subdomain_page_counts.items())  # Sorts by the subdomain (the dict key)
        for domain, pages in sorted_subdomains:
            if ".ics.uci.edu" in domain:  # Ensure we only report for ics.uci.edu subdomains
                report_file.write(f"{domain}: {len(pages)} unique pages\n")