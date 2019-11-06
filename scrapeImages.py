import argparse
import json
import itertools
import logging
import re
import os
import uuid
import sys
from urllib.request import urlopen, Request
import urllib.parse as urlparse
import datetime
import sys, string
import time
from bs4 import BeautifulSoup
import socket
import os.path
image_directory = ""
_tags = []
def configure_logging():
    logger = logging.getLogger('chardet.charsetprober')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler('report.log')
    fh.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('[%(asctime)s %(levelname)s %(module)s]: %(message)s'))
    logger.addHandler(fh)
    logger.addHandler(handler)
    return logger

logger = configure_logging()

REQUEST_HEADER = {
    'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}


def get_soup(url, header):
    response = urlopen(Request(url, headers=header))
    return BeautifulSoup(response, 'html.parser')

def get_query_url(query):
    return "https://www.google.com/search?q=%s&source=lnms&tbm=isch" % query

def deEmojify(inputString):
    return inputString.encode('ascii', 'ignore').decode('ascii')


def extract_images_from_soup(soup):
    image_elements = soup.find_all("div", {"class": "rg_meta"})
    metadata_dicts = (json.loads(e.text) for e in image_elements)
    link_type_records = ((d["ou"], d["ity"], d["pt"], d["pt"]) for d in metadata_dicts)
    return link_type_records

def extract_images(query, num_images):
    url = get_query_url(query)
    ##logger.info("Souping")
    soup = get_soup(url, REQUEST_HEADER)
    #logger.info("Extracting image urls")
    link_type_records = extract_images_from_soup(soup)
    return itertools.islice(link_type_records, num_images)

def get_raw_image(url):
    print("Image url",url)
    req = Request(url, headers=REQUEST_HEADER)
    resp = urlopen(req)
    return resp.read()

def save_image(raw_image, image_counter, image_type, save_directory, alttag, alttitle, url):

    global search_word
    extension = image_type if image_type else 'jpg'
    extensions = ['jpg','png']
    if extension not in extensions:
        extension = 'jpg'
    #file_name = str(uuid.uuid4().hex) + "." + extension
    #file_name = image_file_name
    save_directory = save_directory +"/"+ search_word.replace(' ','-').lower()
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
    
    file_name =  search_word + " " + str(image_counter) + "." + extension
    file_name = file_name.replace(" ","-")
    save_path = os.path.join(save_directory, file_name)
    with open(save_path.lower(), 'wb+') as image_file:
        image_file.write(raw_image)

    saved_image = save_directory + "/" + file_name
    write_image_tag_file(saved_image, alttag, alttitle, url)

def get_file_name_from_url(url):
    a = urlparse.urlparse(url)
    return os.path.basename(a.path)

def write_image_tag_file (image_directory_tag , alt_tag , alt_title, url):

    a = image_directory_tag
    a = a.replace(' ','-').lower()
    #alt_tag = "this is test tag"
    #alt_title = "this is alt title"
    _tags.append(alt_title)

    message = """
        <div class="col-6 col-md-6 col-lg-3" data-aos="fade-up">
          <a href="{URL}" title="{TITLE}" class="d-block photo-item" data-fancybox="gallery">
            <img src="{URL}" alt="{ALT}" class="img-fluid">
            <div class="photo-text-more">
              <span class="icon icon-search"></span>
            </div>
          </a>
        </div>
    """

    # message = """
    # <li class="wall">
    # <a class="thumbimg" href="/view-page/?image_url=/{URL}&title={TITLE}&source={IMGURL}&alt={ALT}" target="_blank" alt="{ALT}" title="{TITLE}">
    # <img src="/{URL}"  alt="{ALT}" title="Find more {TITLE} at {IMGURL}" width="200" height="150"  >
    # </a>
    # </li>
    # """
    alt_tag = deEmojify(alt_tag)
    alt_title = deEmojify(alt_title)
    new_message = message.format(URL=a, ALT=alt_tag, TITLE=alt_title)

    # Write to HTML to file.html
    with open(search_word.replace(" ","-").lower() +".html", "a") as file:
        file.write(new_message)

def download_images_to_dir(images, save_directory, num_images):
    global image_directory
    #logger.info("========" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    #print(list(images))
    for i, (url, image_type,alttag,alttitle) in enumerate(images):
        try:
            image_file_name = get_file_name_from_url(url)
            ##logger.info("Making request (%d/%d): %s : %s : %s", i, num_images, url, image_file_name,alttag)
            alttag = deEmojify(alttag)
            logger.info(" %s : %s", image_file_name, alttag)
            #print(alttag)
            try:
                raw_image = get_raw_image(url)
            except socket.timeout:
                print("timeout")
            except:
                print('new_error')

            save_image(raw_image, i, image_type, save_directory, alttag, alttitle, url)
        except Exception as e:
            logger.exception(e)

def run(query, save_directory, num_images=100):
    
    global image_directory
    image_directory = save_directory
    global _tags
    global search_word
    search_word = query
    query = '+'.join(query.split())

    static_html = """
    <?php include './header.php'; ?>
    """


    new_static_html = static_html.format(title=search_word.replace(" ","-").lower())


    with open(search_word.replace(" ","-").lower() +".php", "a") as file:
        file.write(new_static_html)
    #logger.info("Extracting image links")
    images = extract_images(query, num_images)
    #logger.info("Downloading images")
    download_images_to_dir(images, save_directory, num_images)
    #logger.info("Finished")

    static_html_footer = """
    <?php include './footer.php'; ?>
    """

    with open(search_word.replace(" ","-").lower() +".php", "a", encoding='utf-8') as file:
        file.write(static_html_footer)


def main():
    parser = argparse.ArgumentParser(description='Scrape Google images')
    parser.add_argument('-s', '--search', default='bananas', type=str, help='search term')
    parser.add_argument('-n', '--num_images', default=1, type=int, help='num images to save')
    parser.add_argument('-d', '--directory', default='/Users/gene/Downloads/', type=str, help='save directory')
    args = parser.parse_args()
    timeout = 30
    socket.setdefaulttimeout(timeout)

    values = sys.stdin.read().splitlines()
    for val in values:
        whitelist = set('abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ 1234567890')
        val = ''.join(filter(whitelist.__contains__, val))
        print("{0}".format(val))
        filename = val.replace(" ","-").lower() +".html"
        if (os.path.exists(filename)):
            print('Aleardy Exist')
            continue
        run(val, args.directory, args.num_images)
        time.sleep(20)


if __name__ == '__main__':
    main()
