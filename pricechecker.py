# A desktop app that checks the Roots website for the price on individual items, and emails if price changes

import requests
from bs4 import BeautifulSoup
import random
import time
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def main():
    target_discount = 0.1
    target = 118*(1-target_discount)
    name = 'Emily'
    time_delay_hrs = 24

    # Sand: https://www.roots.com/ca/en/edie-bag-woven-56010377.html?selectedColor=021
    # Black: https://www.roots.com/ca/en/edie-bag-woven-56010382.html?dwvar_56010382_color=Y21&linkedProdID=56010377
    # Natural: https://www.roots.com/ca/en/edie-bag-woven-53357939.html
    # Fawn: https://www.roots.com/ca/en/edie-bag-woven-53371874.html
    urls = [
        'https://www.roots.com/ca/en/edie-bag-woven-56010377.html?selectedColor=021',
        'https://www.roots.com/ca/en/edie-bag-woven-56010382.html?dwvar_56010382_color=Y21&linkedProdID=56010377',
        'https://www.roots.com/ca/en/edie-bag-woven-53357939.html',
        'https://www.roots.com/ca/en/edie-bag-woven-53371874.html'
    ]

    items = scrape_roots(target, urls)
    all_items = items[1]
    init_email_body = write_init_email(name, target_discount, target, time_delay_hrs, all_items)
    auto_email(init_email_body[0], init_email_body[1])

    while True:
        items = scrape_roots(target, urls)
        items_to_email = items[0]
        all_items = items[1]

        if len(items_to_email) > 0:
            email_body = write_auto_email(name, target_discount, items_to_email)
            auto_email(email_body[0], email_body[1])
        print("Checking again in 24 hrs...")
        time.sleep(time_delay_hrs * 60 * 60)


def scrape_roots(target, urls):
    print('Checking Roots...')

    # these come from the dev tab in chrome, network tab, copying a request as cURL, and translating to python
    headers = {
        'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36',
    }

    #from https://stackoverflow.com/questions/41366099/getting-blocked-when-scraping-amazon-even-with-headers-proxies-delay: 
    proxies_list = ["128.199.109.241:8080","113.53.230.195:3128","125.141.200.53:80","125.141.200.14:80","128.199.200.112:138","149.56.123.99:3128","128.199.200.112:80","125.141.200.39:80","134.213.29.202:4444"]
    proxies = {'https//': random.choice(proxies_list)}

    items = []
    for url in urls:
        item_info = {}
        item_info['URL'] = url
        
        # access URL
        page = requests.get(url, headers=headers, proxies=proxies)
        #check for HTTP status code exceptions
        try:
            page.raise_for_status()
        except Exception as exc:
            print('There was a problem: %s' % (exc))

        # get HTML of URL
        soup = BeautifulSoup(page.content, "lxml")

        item = soup.find('div', class_=['product-col-2','product-detail'])

        title = item.find('h1', itemprop='name').get_text().strip()
        style_id = item.find('span', itemprop='productID').get_text().strip()
        colour = item.find('span', class_=["selected-value", "color"]).get_text().strip()
        try:
            price_regular = item.find('span', class_='price-regular').get_text().strip()
            price_regular = float(re.findall("\d+\.\d+", price_regular)[0])
        except: 
            price_regular = 'No Reg. Price listed'
        try:
            price_standard = item.find('span', class_='price-standard').get_text().strip()
            price_standard = float(re.findall("\d+\.\d+", price_standard)[0])
        except: 
            price_standard = 'No Std. Price listed'
        try:
            price_sales = item.find('span', class_='price-sales').get_text().strip()
            price_sales = float(re.findall("\d+\.\d+", price_sales)[0])
        except: 
            price_sales = 'No Sales Price listed'
                
        item_info['Colour'] = colour
        item_info['Title'] = title
        item_info['Style_ID'] = style_id
        item_info['Reg_Price'] = price_regular
        item_info['Std_Price'] = price_standard
        item_info['Sales_Price'] = price_sales
        
        items.append(item_info)

    items_to_email = []
    for item in items:
        rp = item['Reg_Price']
        np = item['Std_Price']
        sp = item['Sales_Price']

        if  (isinstance(rp, float) and rp < target) or (isinstance(np, float) and np < target) or (isinstance(sp, float) and sp < target):
            items_to_email.append(item)

    # will return a tuple
    return (items_to_email, items)

def write_init_email(name, target_discount, target, time_delay_hrs, items):
    print("Writing Initial Email Body...")

    text = """\
        ---Plain Text---
        Wow! You've opted in for the Davis Innovation's Email Notification Program! Big Mistake! <br>
        We'll be checking the below items every {} hours to see if the prices drop atleast {}% 
        (so down to ${} or lower).  If they do, you'll get an email about it.

        These are the items we're checking: {}
        """

    html = """\
        <html>
            <body>
                <p>Hi {},</p>
                <p>
                    Wow! You've opted in for the Davis Innovation's Email Notification Program! Big Mistake! <br>
                    We'll be checking the below items every {} hours to see if the prices drop atleast {}% 
                    (so down to ${} or lower).  If they do, you'll get an email about it.
                </p>
                <p>
                    These are the items we're checking:
                </p>

                <table border = 1px solid black>
                    <th>Title</th>
                    <th>Colour</th>
                    <th>Style ID</th>
                    <th>Link</th>
                    <th>Price</th>
                    <tbody>
                        {}
                    </tbody>
                </table>
                <p>
                    If you wan't to unsubcribe from these notifications, you're SOL!!
                </p>
                <p>
                    Cheers, <br><br>
                    Davis Innovations
                </p>
            </body>
        </html>
        """

    rows=''
    for item in items:
        prices = [item['Reg_Price'], item['Std_Price'], item['Sales_Price']]
        best_price = min([x for x in prices if not isinstance(x, str)])

        data = (
            "<td>"+str(item['Title'])+"</td>"
            + "<td>"+str(item['Colour'])+"</td>"
            + "<td>"+str(item['Style_ID'])+"</td>"
            + "<td>"+str(item['URL'])+"</td>"
            + "<td>"+str(best_price)+"</td>"
        )
            
        rows = rows + "<tr>"+data+"</tr>" 
    
    html = html.format(name, time_delay_hrs, target_discount*100, target, rows)
    text = text.format(name, time_delay_hrs, target_discount*100, target, rows)

    # will return a tuple
    return (html, text)


def write_auto_email(name, target_discount, items):
    print("Writing Auto Email Body...")
    # Create the plain-text and HTML version of message    
    text = """\
    ---Plain Text---
    Roots:
    {}
    """

    html = """\
    <html>
        <body>
            <p>Hi {},</p>
            <h2>The price of the below dropped more than {}%!</h2>
            <table border = 1px solid black>
                <th>Title</th>
                <th>Colour</th>
                <th>Style ID</th>
                <th>Link</th>
                <th>Price</th>
                <tbody>
                    {}
                </tbody>
            </table>
        </body>
    </html>
    """

    rows=''
    for item in items:
        prices = [item['Reg_Price'], item['Std_Price'], item['Sales_Price']]
        best_price = min([x for x in prices if not isinstance(x, str)])

        data = (
            "<td>"+str(item['Title'])+"</td>"
            + "<td>"+str(item['Colour'])+"</td>"
            + "<td>"+str(item['Style_ID'])+"</td>"
            + "<td>"+str(item['URL'])+"</td>"
            + "<td>"+str(best_price)+"</td>"
        )
            
        rows = rows + "<tr>"+data+"</tr>" 
    
    html = html.format(name, target_discount*100,rows)
    text = text.format(rows)

    # will return a tuple
    return (html, text)


def auto_email(html, text):
    #email credentials added to PATH via running nano .bash_profile in terminal and adding them to profile
    from_email = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    to_email = 'striplenaut@gmail.com' #'webdevinci.code@gmail.com'
    port = 587
    server = 'smtp.gmail.com'
    
    message = MIMEMultipart("alternative")
    message["From"] = from_email
    message["To"] = to_email

    subject = "PRICE DROP ALERT! Your Roots Item is Cheap As Hell!!"
    message["Subject"] = subject

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)
    print('Connecting to email server...')
    try:
        smtpObj = smtplib.SMTP(server, port)
        smtpObj.ehlo()
        smtpObj.starttls()
        smtpObj.login(from_email, password)
        print("Sending Email...")
        smtpObj.sendmail(from_email, to_email, message.as_string()) #must send msg as.string() when using HTML and plaintext options
        print('Email Sent!')
    except Exception as e:
        print(e)
    finally:
        smtpObj.quit()


if __name__ == '__main__':
    main()


