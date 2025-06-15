# 备份
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 29 17:32:40 2020

@author: Zhenlin
"""

from bs4 import BeautifulSoup
import urllib.request
import xml.etree.ElementTree as ET
import configparser
from datetime import timedelta, date
import time
import urllib.parse
import socket
from socket import timeout
import os
import random


user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
headers = {'User-Agent': user_agent}
#values = {'name': 'Michael Foord',
#          'location': 'Northampton',
#          'language': 'Python' }
#data = urllib.parse.urlencode(values)
#data = data.encode('ascii')

keyword='编辑'


def get_one_page_news(page_url):
    root='http://www.chinanews.com'
    req = urllib.request.Request(page_url, headers = headers)
    
    try:
        response = urllib.request.urlopen(req, timeout=1)
        html = response.read()
    except Exception as err:
        print(f"Error accessing {page_url}: {str(err)}")
        return []
    
    soup = BeautifulSoup(html,"html.parser") # http://www.crummy.com/software/BeautifulSoup/bs4/doc.zh/
    
    news_pool = []
    news_list = soup.find('div', class_ = "content_list")
    items = news_list.find_all('li')
    for i,item in enumerate(items):
#        print('%d/%d'%(i,len(items)))
        if len(item) == 0:
            continue
        
        a = item.find('div', class_ = "dd_bt").find('a')
        title = a.string
        url = a.get('href')
        if root in url:
            url=url[len(root):]
        
        category = ''
        try:
            category = item.find('div', class_ = "dd_lm").find('a').string
        except Exception as e:
            continue
        
        if category == '图片':
            continue
        
        year = url.split('/')[-3]
        date_time = item.find('div', class_ = "dd_time").string
        date_time = '%s-%s:00'%(year, date_time)
        
        news_info = [date_time, "http://www.chinanews.com"+url, title]
        news_pool.append(news_info)
    return news_pool

def get_news_pool(start_date, end_date):
    news_pool=[]
    delta = timedelta(days=1)
    while start_date <= end_date:
        date_str=start_date.strftime("%Y/%m%d")
        page_url='http://www.chinanews.com/scroll-news/%s/news.shtml'%(date_str)
        print('Extracting news urls at %s'%date_str)
        news_pool += get_one_page_news(page_url)
#        print('done')
        start_date += delta
    return news_pool

def crawl_news(news_pool, target_count, doc_dir_path, doc_encoding, start_id=1):
    i = start_id  # 使用传入的起始ID
    attempts = 0
    max_attempts = len(news_pool) * 2
    
    while i <= target_count and attempts < max_attempts:
        for n, news in enumerate(news_pool):
            if i > target_count:
                break
                
            attempts += 1
            print(f'Processing {i}/{target_count} (attempt {attempts})')
            
            try:
                req = urllib.request.Request(news[1], headers = headers)
                response = urllib.request.urlopen(req, timeout=1)
                html = response.read()
                
                soup = BeautifulSoup(html, "html.parser")
                [s.extract() for s in soup('script')]
                ps = soup.find('div', class_ = "left_zw").find_all('p')
            except Exception as e:
                print(f"Error processing news {news[1]}: {str(e)}")
                continue
            
            body = ''
            for p in ps:
                cur = p.get_text().strip()
                if cur == '':
                    continue
                body += '\t' + cur + '\n'
            body = body.replace(" ", "")
            
            if keyword not in body:  # 仅保留关键词检查
                continue
            
            doc = ET.Element("doc")
            ET.SubElement(doc, "id").text = "%d"%(i)
            ET.SubElement(doc, "url").text = news[1]
            ET.SubElement(doc, "title").text = news[2]
            ET.SubElement(doc, "datetime").text = news[0]
            ET.SubElement(doc, "body").text = body
            tree = ET.ElementTree(doc)
            tree.write(doc_dir_path + "%d.xml"%(i), encoding = doc_encoding, xml_declaration = True)
            
            i += 1
            if i%500 == 0:
                print(f"已生成{i}条新闻数据")
                time.sleep(1)
    
    return i - 1  # 返回最后一个新闻的ID

def get_max_existing_id(doc_dir_path):
    """检测新闻文件夹下已存在的最大新闻ID"""
    try:
        files = os.listdir(doc_dir_path)
        if not files:
            return 0
        xml_files = [f for f in files if f.endswith('.xml')]
        if not xml_files:
            return 0
        max_id = max([int(f.split('.')[0]) for f in xml_files])
        print(f"检测到已存在{len(xml_files)}个新闻文件，最大ID为: {max_id}")
        return max_id
    except Exception as e:
        print(f"检查现有新闻文件时出错: {str(e)}")
        return 0

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    with open(config_path, 'r', encoding='utf-8') as f:
        config.read_file(f)
    
    target_news_count = 2500
    # 检测已存在的最大新闻ID
    next_start_id = get_max_existing_id(config['DEFAULT']['doc_dir_path']) + 1
    print(f"将从ID {next_start_id} 开始继续获取新闻")
    
    while next_start_id <= target_news_count:
        delta = timedelta(days=-5)
        # 根据当前ID计算日期偏移
        end_date = date.today() - timedelta(days=(next_start_id-1)//500)
        start_date = end_date + delta
        
        print(f'\n开始获取{start_date}到{end_date}的新闻')
        news_pool = get_news_pool(start_date, end_date)
        print(f'获取到{len(news_pool)}条新闻链接')
        
        # 传入当前的next_start_id作为起始ID
        last_news_id = crawl_news(news_pool, target_news_count, config['DEFAULT']['doc_dir_path'], 
                                config['DEFAULT']['doc_encoding'], next_start_id)
        
        if last_news_id >= target_news_count:
            print(f'\n成功生成{last_news_id}条新闻数据!')
            break
        else:
            print(f'\n当前已生成到第{last_news_id}条新闻，继续获取...')
            next_start_id = last_news_id + 1  # 更新下一次的起始ID
    
    print('完成!')