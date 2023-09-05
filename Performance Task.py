# -*- coding = utf-8 -*-
# All code were written by the student except as otherwise noted.
#
# requirements:
# beautifulsoup4~=4.12.2
# urllib3~=1.26.15
# pandas~=2.0.0
#
# This program was wrote and tested on python 3.11
#
# This program requires internet connection.
# The website this program crawls is located in China, the process of crawling might be relatively long.
#
# After the data was obtained from the internet, the user can type in a date in the format of year-month-day
# (eg: 2023-4-27) to get all the dishes the dining hall made on that day. The user can also type in a name
# of a dish to get the information of that dish(eg: 红烧鸡腿). You can first get the menu on a day by typing in
# date and then copy and paste a name of a dish from the menu to test the functionality of this program.
#
# There should be no decoding problem for the Chinese characters if the encoder declaration in
# the first line is not removed.

import datetime
import re
import urllib
import urllib.error
import urllib.request

import pandas as pd
from bs4 import BeautifulSoup

# The url where all the menus were listed
baseurl = "https://shanglischool.com/meizhoucaipu/index.php?class1=24&page="


def main():
    urls = get_urls()
    table_list = get_tables(urls)
    dishes = table_to_dish(table_list)
    dates = get_date_list(dishes)
    datedic = dict(zip(dates, (i for i in range(len(dates)))))
    global dishinfolist
    dishinfolist = dish_to_dishinfo(dishes, datedic)

    # Store dishinfolist in an Excel file
    df = pd.DataFrame({
        'Name': [i.name for i in dishinfolist],
        'Type': [', '.join(i.attribute) for i in dishinfolist],
        'Date': [', '.join([j.strftime("%Y-%m-%d") for j in i.appearDate]) for i in dishinfolist],
        'Interval of appearance (days)': [i.freq for i in dishinfolist]
    })
    df.to_excel('dishinfo.xlsx', index=False)

    print('ready')
    print('[year]-[month]-[day]: outputs the menu on that day')
    print('[dish name]: search dish by name')
    while True:
        print(response(input('>>>')))



def response(input):
    """Generates output"""
    ouput = ''
    date = re.findall(r"\d+-\d+-\d+", input)
    if len(date) == 0:
        try:
            # A dictionary that can search a dishinfo object by the name of that dish
            dishinfodic = dict(zip((i.name for i in dishinfolist), (i for i in dishinfolist)))
            ouput = dishinfodic[input].info()
        except KeyError:
            ouput = 'dish does not exist'
    else:
        try:
            date = datetime.datetime.strptime(date[0], "%Y-%m-%d")
        except ValueError:
            return 'invalid date'
        for i in dishinfolist:
            for j in i.appearDate:
                if date.date() == j:
                    ouput += i.name
                    ouput += '\n'
                    break
    if len(ouput) == 0:
        ouput = 'dining hall is not open on this day'
    return ouput


def get_urls():
    """gets the url of a page that contains a table"""
    urllist = []
    c = 0
    while True:
        c += 1
        url = baseurl + str(c)
        print("getting page: " + url + " (" + str(c) + ")")
        findlink = re.compile(r'<a href="(.*?)" target="_self"')
        html = ask_url(url)
        soup = BeautifulSoup(html, "html.parser")
        # The list was created by calling soup.find_all()
        pageelements = soup.find_all('div', class_="media-left")
        if len(pageelements) == 0:
            break
        # The list was used in this iteration, which fills data in the list urllist
        for item in pageelements:
            item = str(item)
            link = re.findall(findlink, item)
            link = "https://shanglischool.com/" + link[0][3:]
            urllist.append(link)

    if len(urllist) == 0:
        raise Exception("cannot find url")
    return urllist


def get_tables(urllist):
    tablelist = []
    n = len(urllist)
    print('found ' + str(n) + ' tables')
    c = 0
    for i in urllist:
        c += 1
        tablelist.append(Table(i))
        print("getting page: " + i, str(round(100 * c / n)) + "%")
    return tablelist


def table_to_dish(tables):
    find_dish = re.compile(r'([^，、]+)')
    dishlist = []
    tables.sort(key=lambda t: (int(t.date0.strftime(
        "%Y")), int(t.date0.strftime("%m")), int(t.date0.strftime("%d"))))
    for table in tables:
        datalist = []
        label = [
            "", "breakfirst", "breakfirst", "breakfirst", "lunch", "lunch", "lunch", "lunch", "lunch", "fruits",
            "dinner", "dinner", "dinner", "dinner", "dinner"
        ]  # The type of the dishes in a row
        for data in table.datalist:
            data = re.findall(find_dish, data)
            datalist.append(data)
        for i in range(1, table.num_of_columns):
            for j in range(1, 15):
                for dishname in datalist[i + table.num_of_columns * j]:
                    if dishname != "<br/>":
                        dishlist.append(Dish(dishname, table.date0 + datetime.timedelta(days=+(i - 1)), label[j]))
    return dishlist


def dish_to_dishinfo(dishlist, datedic):
    dishinfolist = []
    dishlist.sort(key=lambda t: t.name)
    lastdish = dishlist[0]
    dishinfolist.append(Dishinfo(lastdish.name, datedic))
    for i in dishlist:
        if i.name == lastdish.name:
            dishinfolist[-1].add_appear_history(i.date, i.attribute, datedic.get(i.date))
        else:
            dishinfolist.append(Dishinfo(i.name, datedic))
            dishinfolist[-1].add_appear_history(i.date, i.attribute, datedic.get(i.date))
        lastdish = i
    return dishinfolist


def get_date_list(dishlist):
    datelist = []
    for i in dishlist:
        datelist.append(i.date)
    datelist = list(set(datelist))
    datelist.sort(key=lambda t: (int(t.strftime("%Y")), int(t.strftime("%m")),
                                 int(t.strftime("%d"))))
    return datelist



def ask_url(url):
    """Returns the html file in string according to the url given. Not wirten by the student"""
    head = {
        "User-Agent":
            "Mozilla / 5.0(Windows NT 10.0; Win64; x64) AppleWebKit / 537.36(KHTML, like Gecko) Chrome / "
            "89.0.4389.90Safari / 537.36Edg / 89.0.774.63 "
    }
    request = urllib.request.Request(url, headers=head)
    html = ""
    try:
        response = urllib.request.urlopen(request)
        html = response.read().decode("utf-8")
    except urllib.error.URLError as e:
        if hasattr(e, "code"):
            print(e.code)
        if hasattr(e, "reason"):
            print(e.reason)
    return html



class Dishinfo:
    '''A class that can store dish as an instance'''
    def __init__(self, name, datedic):
        self.name = name
        self.attribute = []
        self.appearDate = []
        self.freq = 0
        self.appearIndex = []
        self.datedic = datedic

    # Calculates the frequency of the appearance of a dish
    def add_appear_history(self, addate, addattribute, dateindex):
        self.appearDate.append(addate)
        self.attribute.append(addattribute)
        self.appearIndex.append(dateindex)
        self.attribute = list(set(self.attribute))
        appeardelta = [self.appearIndex[0]]
        for i in range(1, len(self.appearIndex)):
            appeardelta.append(self.appearIndex[i] - self.appearIndex[i - 1])
        appeardelta.append(len(self.datedic) - self.appearIndex[-1])
        self.freq = round(sum(appeardelta) / len(appeardelta))

    def info(self):
        ouput = 'Name: ' + self.name + "\n" + 'Type: '
        for j in self.attribute:
            ouput += j + '\n'
        ouput += "Date: \n"
        for j in self.appearDate:
            ouput += j.strftime("%Y-%m-%d") + '\n'
        ouput += "interval of appearance: " + str(self.freq) + "days\n"
        return ouput


class Table:
    """A class that can store all the weekly menu as instance"""
    def __init__(self, url):
        self.date1 = None
        self.date0 = None
        self.num_of_columns = None
        self.get_date(url)
        self.datalist = self.get_data(url)

    # Gets the date
    def get_date(self, url):
        findyear = re.compile(r'<span>(\d\d\d\d)\D+')
        findmonth = re.compile(r'\D+(\d+)月\d+日')
        finddate = re.compile(r'\D+\d+月(\d+)日')
        soup = BeautifulSoup(ask_url(url), "html.parser")
        data = soup.find_all('section', class_="details-title border-bottom1")
        data = str(data[0])
        d0 = int(re.findall(finddate, data)[0])
        m0 = int(re.findall(findmonth, data)[0])
        d1 = int(re.findall(finddate, data)[1])
        m1 = int(re.findall(findmonth, data)[1])
        y0 = int(re.findall(findyear, data)[0])
        if (datetime.date(2020, m1, d1) - datetime.date(2020, m0, d0)).days < 0:
            y1 = y0 + 1
        else:
            y1 = y0
        self.date0 = datetime.date(y0, m0, d0)
        self.date1 = datetime.date(y1, m1, d1)
        self.num_of_columns = (self.date1 - self.date0).days + 2

    # Gets the menu
    def get_data(self, url):
        finddata1 = re.compile(r'>([^s]*?)</span>')
        finddata2 = re.compile(r'>([^s]+)</td>')
        soup = BeautifulSoup(ask_url(url), "html.parser")
        datalist = []
        for row in soup.find_all('td'):
            row = str(row)
            if len(re.findall(finddata1, row)) != 0:
                block = re.findall(finddata1, row)
            elif len(re.findall(finddata2, row)) != 0:
                block = re.findall(finddata2, row)
            if block:
                data = ""
                for i in block:
                    i = "".join(i.split())
                    data += i
                if len(datalist) % self.num_of_columns == 0 and not (data == "<br/>" or "餐" in data or "小学" in data):
                    datalist.append("<br/>")
                datalist.append(data)
        return datalist


class Dish:
    def __init__(self, name, date, attribute):
        self.name = name
        self.date = date
        self.attribute = attribute


if __name__ == "__main__":
    main()
