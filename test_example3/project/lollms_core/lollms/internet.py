from ascii_colors import ASCIIColors, trace_exception
def get_favicon_url(url):
    import requests
    from bs4 import BeautifulSoup
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        favicon_link = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
        
        if favicon_link:
            favicon_url = favicon_link['href']
            if not favicon_url.startswith('http'):
                favicon_url = url + favicon_url
            return favicon_url
    except:
        ASCIIColors.warning(f"Couldn't get fav icon from {url}")
    return None


def get_root_url(url):
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    root_url = parsed_url.scheme + "://" + parsed_url.netloc
    return root_url


def format_url_parameter(value:str):
    encoded_value = value.strip().replace("\"","")
    return encoded_value


def get_relevant_text_block(
                                url,
                                driver,
                                config,
                                vectorizer,
                                title=None,
                                brief=None
                            ):
    try:
        from bs4 import BeautifulSoup    
        # Load the webpage
        driver.get(url)

        # Wait for JavaScript to execute and get the final page source
        html_content = driver.page_source

        # Parse the HTML content
        soup = BeautifulSoup(html_content, "html.parser")
        # Example: Remove all <script> and <style> tags
        for script in soup(["script", "style"]):
            script.extract()

        all_text = soup.get_text()
        # Example: Remove leading/trailing whitespace and multiple consecutive line breaks
        document_id = {
            'url':url
        }
        document_id["title"] = title
        document_id["brief"] = brief
        vectorizer.add_document(document_id,all_text, config.internet_vectorization_chunk_size, config.internet_vectorization_overlap_size)
    except:
        ASCIIColors.warning(f"Couldn't scrape: {url}")

def extract_results(url, max_num, driver=None):
    from bs4 import BeautifulSoup    

    # Load the webpage
    driver.get(url)

    # Wait for JavaScript to execute and get the final page source
    html_content = driver.page_source

    # Parse the HTML content
    soup = BeautifulSoup(html_content, "html.parser")

    # Detect that no outputs are found
    Not_found = soup.find("No results found")

    if Not_found : 
        return []    

    # Find the <ol> tag with class="react-results--main"
    ol_tag = soup.find("ol", class_="react-results--main")

    # Initialize an empty list to store the results
    results_list = []

    try:
        # Find all <li> tags within the <ol> tag
        li_tags = ol_tag.find_all("li")

        # Loop through each <li> tag, limited by max_num
        for index, li_tag in enumerate(li_tags):
            if index > max_num*3:
                break

            try:
                # Find the three <div> tags within the <article> tag
                div_tags = li_tag.find_all("div")

                # Extract the link, title, and content from the <div> tags
                links = div_tags[0].find_all("a")
                href_value = links[1].get('href')
                span = links[1].find_all("span")
                link = span[0].text.strip()

                title = div_tags[2].text.strip()
                content = div_tags[3].text.strip()

                # Add the extracted information to the list
                results_list.append({
                    "link": link,
                    "href": href_value,
                    "title": title,
                    "brief": content
                })
            except Exception:
                pass
    except:
        pass
    return results_list
    
def internet_search(query, chromedriver_path, config, model = None, quick_search:bool=False):
    """
    """

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from safe_store.text_vectorizer import TextVectorizer, VectorizationMethod

    vectorizer = TextVectorizer(VectorizationMethod.TFIDF_VECTORIZER, model = model)

    formatted_text = ""
    nb_non_empty = 0
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode

    # Set path to chromedriver executable (replace with your own path)
    if chromedriver_path is None: 
        chromedriver_path = ""#"/snap/bin/chromium.chromedriver"    

    # Create a new Chrome webdriver instance
    try:
        driver = webdriver.Chrome(executable_path=chromedriver_path, options=chrome_options)
    except:
        driver = webdriver.Chrome(options=chrome_options)

    results = extract_results(
                                f"https://duckduckgo.com/?q={format_url_parameter(query)}&t=h_&ia=web",
                                config.internet_nb_search_pages,
                                driver
                            )
    
    for i, result in enumerate(results):
        title = result["title"]
        brief = result["brief"]
        href = result["href"]
        if quick_search:
            vectorizer.add_document({'url':href, 'title':title, 'brief': brief}, brief)
        else:
            get_relevant_text_block(href, driver, config, vectorizer, title, brief)
        nb_non_empty += 1
        if nb_non_empty>=config.internet_nb_search_pages:
            break
    vectorizer.index()
    # Close the browser
    driver.quit()

    docs, sorted_similarities, document_ids = vectorizer.recover_text(query, config.internet_vectorization_nb_chunks)
    return docs, sorted_similarities, document_ids
