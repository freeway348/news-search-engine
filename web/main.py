# -*- coding: utf-8 -*-
__author__ = 'lcl'

from flask import Flask, render_template, request
from search_engine import SearchEngine
import xml.etree.ElementTree as ET
import sqlite3
import configparser
import time
import jieba
import os  # 修复：全局导入os

app = Flask(__name__)

# 全局变量初始化，避免未定义报错
dir_path = ''
db_path = ''
page = []
keys = ''
checked = ['checked="true"', '', '']
doc_id = []

def init():
    try:
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
        if not config.read(config_path, encoding='utf-8'):
            raise FileNotFoundError(f"无法读取配置文件: {config_path}")
        global dir_path, db_path
        dir_path = os.path.abspath(os.path.join(
            os.path.dirname(config_path),
            config.get('DEFAULT', 'doc_dir_path')
        ))
        db_path = os.path.abspath(os.path.join(
            os.path.dirname(config_path),
            config.get('DEFAULT', 'db_path')
        ))
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"新闻数据目录不存在: {dir_path}")
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
    except Exception as e:
        print(f"配置初始化错误: {str(e)}")
        raise

@app.route('/')
def main():
    init()
    return render_template('search.html', error=True)


# 读取表单数据，获得doc_ID
@app.route('/search/', methods=['POST'])
def search():
    try:
        global keys
        global checked
        checked = ['checked="true"', '', '']
        keys = request.form['key_word']
        
        if not keys:
            return render_template('search.html', error=False)
            
        start_time = time.perf_counter()  # 替换已弃用的 time.clock()
        flag, page = searchidlist(keys)
        
        if flag == 0:
            return render_template('search.html', error=False)
            
        docs = cut_page(page, 0)
        end_time = time.perf_counter()
        print(f"搜索耗时: {end_time - start_time:.3f}秒")
        
        return render_template('high_search.html', 
                             checked=checked, 
                             key=keys, 
                             docs=docs, 
                             page=page,
                             error=True)
                             
    except Exception as e:
        print(f'搜索发生错误: {str(e)}')
        return render_template('search.html', error=True, message="搜索过程中发生错误")


def searchidlist(key, selected=0):
    try:
        global page
        global doc_id
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
        se = SearchEngine(config_path, 'utf-8')
        flag, id_scores = se.search(key, selected)
        if not id_scores:
            return 0, []
        # 返回docid列表
        doc_id = [i for i, s in id_scores]
        page = []
        for i in range(1, (len(doc_id) // 10 + 2)):
            page.append(i)
        return flag, page
    except Exception as e:
        print(f"搜索列表获取失败: {str(e)}")
        return 0, []


def cut_page(page, no):
    global doc_id
    docs = find(doc_id[no*10:page[no]*10])
    return docs


# 将需要的数据以字典形式打包传递给search函数
def find(docid, extra=False):
    docs = []
    global dir_path, db_path
    for id in docid:
        try:
            # 使用os.path.join构建完整路径
            xml_path = os.path.join(dir_path, f'{id}.xml')
            if not os.path.exists(xml_path):
                print(f"警告：文件不存在：{xml_path}")
                continue
                
            root = ET.parse(xml_path).getroot()
            url = root.find('url').text
            title = root.find('title').text
            body = root.find('body').text
            snippet = body[0:120] + '……' if body else ''
            datetime = root.find('datetime').text
            time_str = datetime.split(' ')[0] if datetime else ''
            
            doc = {
                'url': url,
                'title': title,
                'snippet': snippet,
                'datetime': datetime,
                'time': time_str,
                'body': body,
                'id': id,
                'extra': []
            }
            
            if extra:
                temp_doc = get_k_nearest(db_path, id)
                for i in temp_doc:
                    temp_path = os.path.join(dir_path, f'{i}.xml')
                    if os.path.exists(temp_path):
                        temp_root = ET.parse(temp_path).getroot()
                        temp_title = temp_root.find('title').text
                        doc['extra'].append({'id': i, 'title': temp_title})
                    
            docs.append(doc)
        except Exception as e:
            print(f"处理文档 {id} 时出错: {str(e)}")
            continue
            
    return docs


@app.route('/search/page/<page_no>/', methods=['GET'])
def next_page(page_no):
    try:
        page_no = int(page_no)
        docs = cut_page(page, (page_no-1))
        return render_template('high_search.html', checked=checked, key=keys, docs=docs, page=page,
                               error=True)
    except:
        print('next error')


@app.route('/search/<key>/', methods=['POST'])
def high_search(key):
    try:
        selected = int(request.form['order'])
        for i in range(3):
            if i == selected:
                checked[i] = 'checked="true"'
            else:
                checked[i] = ''
        flag,page = searchidlist(key, selected)
        if flag==0:
            return render_template('search.html', error=False)
        docs = cut_page(page, 0)
        return render_template('high_search.html',checked=checked ,key=keys, docs=docs, page=page,
                               error=True)
    except:
        print('high search error')


@app.route('/search/<id>/', methods=['GET', 'POST'])
def content(id):
    try:
        doc = find([id], extra=True)
        return render_template('content.html', doc=doc[0])
    except:
        print('content error')


def get_k_nearest(db_path, docid, k=5):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM knearest WHERE id=?", (docid,))
    docs = c.fetchone()
    #print(docs)
    conn.close()
    return docs[1: 1 + (k if k < 5 else 5)]  # max = 5


if __name__ == '__main__':
    import os
    import configparser
    
    # 获取项目根目录和相关路径
    ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
    CONFIG_PATH = os.path.join(ROOT_DIR, 'config.ini')
    DATA_DIR = os.path.join(ROOT_DIR, 'data')
    
    # 检查配置文件
    if not os.path.exists(CONFIG_PATH):
        print(f"错误：配置文件不存在：{CONFIG_PATH}")
        exit(1)
        
    # 验证配置文件内容
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding='utf-8')
    required_configs = ['doc_dir_path', 'db_path', 'stop_words_path']
    for item in required_configs:
        if item not in config['DEFAULT']:
            print(f"错误：配置文件缺少必要项：{item}")
            exit(1)
    
    # 检查必要的文件和目录
    required_paths = [
        os.path.join(DATA_DIR, 'news'),          # 新闻数据目录
        os.path.join(DATA_DIR, 'ir.db'),         # 数据库文件
        os.path.join(DATA_DIR, 'stop_words.txt') # 停用词表
    ]
    
    for path in required_paths:
        if not os.path.exists(path):
            print(f"错误：找不到必要的文件或目录：{path}")
            exit(1)
    
    # 初始化jieba分词
    jieba.initialize()
    print("系统初始化完成...")
    
    # 启动Flask应用
    app.run(debug=True)  # 开启调试模式以查看详细错误信息