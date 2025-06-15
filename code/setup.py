# -*- coding: utf-8 -*-
"""
Created on Fri Dec 25 00:04:40 2015

@author: bitjoy.net
"""

from spider import get_news_pool
from spider import crawl_news
from index_module import IndexModule
from recommendation_module import RecommendationModule
from datetime import *
import urllib.request
import configparser
import time
import random
import os  # 添加os模块导入

def get_max_page(root):
    response = urllib.request.urlopen(root)
    html = str(response.read())
    html = html[html.find('var maxPage =') : ]
    html = html[:html.find(';')]
    max_page = int(html[html.find('=') + 1 : ])
    #print(max_page)
    return(max_page)

def crawling():
    print('-----start crawling time: %s-----'%(datetime.today()))
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    with open(config_path, 'r', encoding='utf-8') as f:
        config.read_file(f)
    root = 'http://news.sohu.com/1/0903/61/subject212846158'
    max_page = get_max_page(root+'.shtml')
    news_pool = get_news_pool(root, max_page, max_page - 5)
    crawl_news(news_pool, 140, config['DEFAULT']['doc_dir_path'], config['DEFAULT']['doc_encoding'])

if __name__ == "__main__":
    print('-----start time: %s-----'%(datetime.today()))
    
    #抓取新闻数据 #20200404，可替换为spider.chinanews.com.py抓取新闻 
    #crawling()
    
    #构建索引
    print('-----start indexing time: %s-----'%(datetime.today()))
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
    with open(config_path, 'r', encoding='utf-8') as f:
        config.read_file(f)
    im = IndexModule(config_path, 'utf-8')
    im.construct_postings_lists()
    
    #推荐阅读
    print('-----start recommending time: %s-----'%(datetime.today()))
    rm = RecommendationModule(config_path, 'utf-8')
    rm.find_k_nearest(5, 25)
    print('-----finish time: %s-----'%(datetime.today()))