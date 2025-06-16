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
import json
import re
import ssl

# 创建未经验证的SSL上下文（用于处理SSL证书问题）
ssl._create_default_https_context = ssl._create_unverified_context

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
headers = {
    'User-Agent': user_agent,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.sohu.com/'
}

keyword='编辑'

def get_sohu_news_pool(target_count):
    """获取搜狐新闻池"""
    print('正在获取搜狐新闻列表...')
    news_pool = []
    
    # 搜狐新闻专题页面链接
    topic_urls = [
        'https://www.sohu.com/xchannel/tag?key=%E6%96%B0%E9%97%BB-%E6%97%B6%E6%94%BF',  # 时政
        'https://www.sohu.com/xchannel/tag?key=%E5%86%9B%E4%BA%8B',  # 军事
        'https://www.sohu.com/xchannel/tag?key=%E8%AD%A6%E6%B3%95',  # 警法
    ]
    
    headers.update({
        'Host': 'www.sohu.com',
        'Referer': 'https://www.sohu.com',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    })
    
    seen_urls = set()
    seen_titles = set()
    
    # 遍历每个专题页面
    for topic_url in topic_urls:
        try:
            print(f'获取专题新闻: {urllib.parse.unquote(topic_url.split("key=")[1])}')
            req = urllib.request.Request(topic_url, headers=headers)
            response = urllib.request.urlopen(req, timeout=15)
            html = response.read().decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(html, "html.parser")
            
            # 查找新闻列表区域
            news_list = soup.find('div', class_='feed-list')
            if not news_list:
                continue
            
            # 获取所有新闻项
            news_items = news_list.find_all('div', class_=['feed-item', 'news-box'])
            
            for item in news_items:
                try:
                    # 查找新闻链接
                    link = item.find('a', attrs={'href': True, 'title': True})
                    if not link:
                        continue
                        
                    url = link['href']
                    title = link['title'].strip()
                    
                    # 处理相对URL
                    if not url.startswith('http'):
                        url = 'https:' + url if url.startswith('//') else 'https://www.sohu.com' + url
                        
                    # 验证是否为有效新闻URL
                    if not ('www.sohu.com/a/' in url):
                        continue
                        
                    # 过滤视频等非文章内容
                    if any(x in url.lower() for x in ['video', 'pic', 'tv', 'subject']):
                        continue
                        
                    # 检查标题有效性
                    if not title or len(title) < 10:
                        continue
                        
                    # 去重检查
                    if url in seen_urls or title in seen_titles:
                        continue
                        
                    # 提取发布时间
                    time_span = item.find(['span', 'div'], class_=['time', 'publish-time'])
                    pub_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    if time_span:
                        time_text = time_span.get_text().strip()
                        if re.search(r'\d{4}-\d{2}-\d{2}', time_text):
                            pub_time = time_text
                            
                    seen_urls.add(url)
                    seen_titles.add(title)
                    news_pool.append([pub_time, url, title])
                    
                except Exception as e:
                    continue
            
            print(f'当前获取到{len(news_pool)}条不重复新闻')
            time.sleep(random.uniform(2, 3))
            
        except Exception as err:
            print(f"访问专题页面出错: {str(err)}")
            continue
    
    print(f'共获取到{len(news_pool)}条搜狐新闻链接')
    return news_pool[:target_count]

def get_one_page_news(page_url):
    root='http://www.chinanews.com'
    req = urllib.request.Request(page_url, headers = headers)
    
    try:
        response = urllib.request.urlopen(req, timeout=15)
        html = response.read()
    except Exception as err:
        print(f"访问中国新闻网出错: {str(err)}")
        return []
    
    soup = BeautifulSoup(html,"html.parser", from_encoding='utf-8')
    
    news_pool = []
    news_list = soup.find('div', class_ = "content_list")
    if not news_list:
        print("未找到新闻列表")
        return news_pool
        
    items = news_list.find_all('li')
    for i,item in enumerate(items):
        if len(item) == 0:
            continue
        
        try:
            a = item.find('div', class_ = "dd_bt").find('a')
            if not a:
                continue
                
            title = a.get_text().strip()
            url = a.get('href')
            if not url:
                continue
                
            if root in url:
                url = url[len(root):]
            
            category = ''
            try:
                category_div = item.find('div', class_ = "dd_lm")
                if category_div:
                    category_a = category_div.find('a')
                    if category_a:
                        category = category_a.get_text().strip()
            except Exception as e:
                pass
            
            if category == '图片':
                continue
            
            try:
                year = url.split('/')[-3]
                date_time_div = item.find('div', class_ = "dd_time")
                if date_time_div:
                    date_time_str = date_time_div.get_text().strip()
                    date_time = f'{year}-{date_time_str}:00'
                else:
                    date_time = time.strftime("%Y-%m-%d %H:%M:%S")
            except:
                date_time = time.strftime("%Y-%m-%d %H:%M:%S")
            
            news_info = [date_time, "http://www.chinanews.com" + url, title]
            news_pool.append(news_info)
        except Exception as e:
            print(f"处理新闻项出错: {str(e)}")
            continue
            
    return news_pool

def get_news_pool(start_date, end_date):
    news_pool=[]
    delta = timedelta(days=1)
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y/%m%d")
        page_url = f'http://www.chinanews.com/scroll-news/{date_str}/news.shtml'
        print(f'获取{date_str}的新闻')
        
        page_news = get_one_page_news(page_url)
        news_pool.extend(page_news)
        print(f'获取到{len(page_news)}条新闻链接')
        
        current_date += delta
        # 添加随机延时
        time.sleep(random.uniform(0.5, 1.5))
        
    return news_pool

def parse_sohu_news(url):
    """解析搜狐新闻详情页"""
    try:
        headers.update({
            'Host': urllib.parse.urlparse(url).netloc,
            'Referer': 'https://www.sohu.com'
        })
        
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=15)
        html = response.read().decode('utf-8', errors='ignore')
        
        soup = BeautifulSoup(html, "html.parser")
        
        # 提取标题
        title = None
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text().strip()
            
        if not title:
            print(f"未找到标题: {url}")
            return None
            
        # 提取正文 - 针对搜狐新闻的特定结构
        article = soup.find('article', id='mp-editor') or \
                 soup.find('article', class_='article') or \
                 soup.find('div', class_='article') or \
                 soup.find('div', id='contentText')
                 
        body = ''
        if article:
            # 移除无用元素
            for tag in article.find_all(['script', 'style']):
                tag.decompose()
                
            for p in article.find_all(['p', 'div']):
                text = p.get_text().strip()
                if text and len(text) > 2 and \
                   not text.startswith('责任编辑：') and \
                   not text.startswith('声明：'):
                    body += '\t' + text + '\n'
                    
        if not body or len(body) < 100:
            print(f"内容无效: {url}")
            return None
            
        return {
            'title': title,
            'datetime': time.strftime("%Y-%m-%d %H:%M:%S"),
            'body': body
        }
        
    except Exception as e:
        print(f"解析搜狐新闻出错 {url}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

def crawl_news(news_pool, target_count, doc_dir_path, doc_encoding, start_id=1, source='chinanews'):
    i = start_id
    processed_count = 0
    skipped_count = 0
    
    if not news_pool:
        print("新闻池为空，无法爬取")
        return start_id - 1
    
    print(f"开始爬取{len(news_pool)}条新闻链接...")
    
    for n, news in enumerate(news_pool):
        if i > target_count:
            print(f"已达到目标数量 {target_count}")
            break
            
        print(f'处理 {i}/{target_count} (来源: {source}, 进度: {n+1}/{len(news_pool)})')
        
        try:
            if source == 'sohu':
                parsed_news = parse_sohu_news(news[1])
                if not parsed_news:
                    skipped_count += 1
                    continue
                    
                title = parsed_news['title']
                datetime = parsed_news['datetime']
                body = parsed_news['body']
            else:
                req = urllib.request.Request(news[1], headers=headers)
                try:
                    response = urllib.request.urlopen(req, timeout=15)
                    html = response.read()
                except (timeout, socket.error) as e:
                    print(f"网络错误: {str(e)}")
                    skipped_count += 1
                    continue
                
                try:
                    soup = BeautifulSoup(html, "html.parser", from_encoding='utf-8')
                    [s.extract() for s in soup('script')]
                    content_div = soup.find('div', class_="left_zw")
                    if not content_div:
                        print("未找到内容区域")
                        skipped_count += 1
                        continue
                        
                    ps = content_div.find_all('p')
                    
                    body = ''
                    for p in ps:
                        cur = p.get_text().strip()
                        if cur:
                            body += '\t' + cur + '\n'
                    body = body.replace(" ", "")
                    
                    # 检查新闻内容是否有效
                    if len(body) < 100:  # 内容过短可能是无效新闻
                        print(f"内容过短: {len(body)}字符")
                        skipped_count += 1
                        continue
                        
                    title = news[2]
                    datetime = news[0]
                except Exception as e:
                    print(f"解析错误: {str(e)}")
                    skipped_count += 1
                    continue
            
            # 关键词检查
            if keyword not in body:
                skipped_count += 1
                continue
            
            # 保存新闻
            doc = ET.Element("doc")
            ET.SubElement(doc, "id").text = str(i)
            ET.SubElement(doc, "url").text = news[1]
            ET.SubElement(doc, "title").text = title
            ET.SubElement(doc, "datetime").text = datetime
            ET.SubElement(doc, "body").text = body
            
            file_path = os.path.join(doc_dir_path, f"{i}.xml")
            tree = ET.ElementTree(doc)
            tree.write(file_path, encoding=doc_encoding, xml_declaration=True)
            
            i += 1
            processed_count += 1
            
            if processed_count % 50 == 0:
                print(f"已成功处理{processed_count}条新闻，跳过{skipped_count}条")
                time.sleep(1)
                
        except Exception as e:
            print(f"处理新闻时发生错误: {str(e)}")
            skipped_count += 1
            continue
    
    print(f"处理完成：成功{processed_count}条，跳过{skipped_count}条，最后ID: {i-1}")
    return i - 1

def get_max_existing_id(doc_dir_path):
    """检测新闻文件夹下已存在的最大新闻ID"""
    try:
        files = os.listdir(doc_dir_path)
        if not files:
            return 0
        xml_files = [f for f in files if f.endswith('.xml') and f.split('.')[0].isdigit()]
        if not xml_files:
            return 0
            
        ids = []
        for f in xml_files:
            try:
                ids.append(int(f.split('.')[0]))
            except:
                continue
                
        if not ids:
            return 0
            
        max_id = max(ids)
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
    
    total_target_news = 5000  # 总目标5000条新闻
    chinanews_target = 2500   # 中国新闻网目标2500条
    sohu_target = 2500        # 搜狐网目标2500条
    
    # 检测已存在的最大新闻ID
    next_start_id = get_max_existing_id(config['DEFAULT']['doc_dir_path']) + 1
    print(f"将从ID {next_start_id} 开始继续获取新闻")
    
    # 初始化变量
    last_news_id = next_start_id - 1
    
    # 第一步：从中国新闻网获取新闻（如果需要）
    if next_start_id <= chinanews_target:
        print("\n===== 开始从中国新闻网获取新闻 =====")
        
        while last_news_id < chinanews_target:
            # 计算需要爬取的数量
            remaining = chinanews_target - last_news_id
            print(f"需要在中国新闻网获取{remaining}条新闻")
            
            # 根据当前ID计算日期偏移
            days_offset = max(1, (last_news_id) // 100)
            end_date = date.today() - timedelta(days=days_offset)
            start_date = end_date - timedelta(days=5)
            
            print(f'获取{start_date}到{end_date}的新闻')
            news_pool = get_news_pool(start_date, end_date)
            
            if not news_pool:
                print("未获取到新闻，尝试下一个时间段")
                # 扩大日期范围
                start_date = end_date - timedelta(days=10)
                end_date = end_date - timedelta(days=1)
                news_pool = get_news_pool(start_date, end_date)
                
            if not news_pool:
                print("多次尝试后仍未能获取新闻，跳过中国新闻网阶段")
                last_news_id = chinanews_target
                break
                
            print(f'获取到{len(news_pool)}条新闻链接')
            
            # 爬取新闻
            last_news_id = crawl_news(
                news_pool, 
                chinanews_target, 
                config['DEFAULT']['doc_dir_path'], 
                config['DEFAULT']['doc_encoding'], 
                last_news_id + 1, 
                'chinanews'
            )
            
            print(f'当前中国新闻网新闻ID: {last_news_id}')
            
            # 如果达到目标或没有更多新闻，退出循环
            if last_news_id >= chinanews_target:
                break
            
            # 添加短暂延迟
            time.sleep(random.uniform(2, 3))
    
    # 确保中国新闻网部分结束后的下一个ID
    sohu_start_id = max(last_news_id + 1, chinanews_target + 1)
    
    # 第二步：从搜狐网获取新闻
    if sohu_start_id <= total_target_news:
        print(f"\n===== 开始从搜狐网获取新闻 (起始ID: {sohu_start_id}) =====")
        
        while sohu_start_id < total_target_news:
            # 获取搜狐新闻池
            sohu_news_pool = get_sohu_news_pool(100)  # 每次获取100条链接
            
            if not sohu_news_pool:
                print("本轮未获取到搜狐新闻，等待后重试")
                time.sleep(random.uniform(3, 5))
                continue
                
            # 爬取新闻
            last_news_id = crawl_news(
                sohu_news_pool,
                total_target_news,
                config['DEFAULT']['doc_dir_path'],
                config['DEFAULT']['doc_encoding'],
                sohu_start_id,
                'sohu'
            )
            
            if last_news_id >= total_target_news:
                break
                
            sohu_start_id = last_news_id + 1
            print(f"当前已处理到ID: {last_news_id}, 继续获取新闻...")
            time.sleep(random.uniform(2, 3))
    
    print(f'\n爬虫任务完成! 最终新闻ID: {last_news_id}')