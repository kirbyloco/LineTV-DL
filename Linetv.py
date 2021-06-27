import json
import os
import re
import subprocess

import requests
from lxml import etree


with open('config.json') as f:
    config = json.load(f)

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
session = requests.Session()
session.headers.update({'User-Agent': UA})

if config['access_token']:
    session.headers.update({'authorization': config['access_token']})


class Parser():
    def __init__(self, dramaid: str):
        self.dramaid = str(dramaid)
        self.eps = []
        self._behind = {}
        self.html = session.get(f'https://www.linetv.tw/drama/{self.dramaid}')
        self.get_eps()
        self.get_behind()

    def get_eps(self):
        parser = etree.HTML(self.html.text)
        for _ in parser.xpath('//li/a/h3'):
            self.eps.append(re.findall(r'(\d+)', _.text)[0])

    def get_behind(self):
        parser = etree.HTML(self.html.text)
        data = json.loads(parser.xpath(
            '//script[@type="application/ld+json"]')[2].text)
        for _trailer in data['trailer']:
            self._behind[_trailer['name']] = _trailer['contentUrl']

    def behind(self):
        num = 0
        for _title in self._behind.keys():
            num += 1
            print(f'{num} {_title}')
        return self._behind[list(self._behind.keys())
                            [int(input('請輸入需要的編號：')) - 1]]


class DL:
    class Drama():
        def __init__(self, dramaid: str, ep: str):
            self.dramaid = str(dramaid)
            self.dramaname = ''
            self.ep = str(ep)
            self.keyId = ''
            self.keyType = ''
            self.m3u8 = ''
            self.subtitle = ''
            self.check_ffmpeg()
            self.get_m3u8()
            self.get_m3u8_key()
            self.dl_video()
            print('下載完成')
            # shutil.rmtree('.')

        def check_ffmpeg(self):
            try:
                subprocess.Popen(
                    'ffmpeg -h', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except FileNotFoundError:
                print('本項目需要ffmpeg，請手動安裝ffmpeg')
                raise

        def get_m3u8(self):
            req = session.get(
                f'https://www.linetv.tw/api/part/{self.dramaid}/eps/{self.ep}/part')
            try:
                parser = req.json()['epsInfo']['source'][0]['links'][0]
            except KeyError:
                print(req.json()['message'])
                return
            self.dramaname = req.json()['dramaInfo']['name']
            self.keyId = parser['keyId']
            self.keyType = parser['keyType']
            self.m3u8 = parser['link']
            if 'subtitle' in parser:
                self.subtitle = parser['subtitle']

        def get_m3u8_key(self):
            data = {'keyType': self.keyType, 'keyId': self.keyId,
                    'dramaId': int(self.dramaid), 'eps': int(self.ep)}
            req = session.post(
                'https://www.linetv.tw/api/part/dinosaurKeeper', json=data)
            token = req.json()['token']
            key = requests.get(
                'https://keydeliver.linetv.tw/jurassicPark', headers={'authentication': token})
            with open(os.path.join('.', 'm3u8.key'), 'wb') as f:
                f.write(key.content)

        def dl_video(self):
            urlfix = re.findall(r'(.*\/)\d+.*\d', self.m3u8)[0]
            m3u8url = f'{urlfix}1080/{self.dramaid}-eps-{self.ep}_1080p.m3u8'
            m3u8 = session.get(m3u8url)
            m3u8 = re.sub(r'https://keydeliver.linetv.tw/jurassicPark',
                          'm3u8.key', m3u8.text)
            m3u8 = re.sub(f'{self.dramaid}-eps-{self.ep}_1080p.ts',
                          f'{urlfix}1080/{self.dramaid}-eps-{self.ep}_1080p.ts', m3u8)
            with open(os.path.join('.', f'{self.dramaid}-eps-{self.ep}_1080p.m3u8'), 'w') as f:
                f.write(m3u8)

            print(f'正在下載：{self.dramaname} 第{self.ep}集')
            output = os.path.join('.', f'{self.dramaname}-E{self.ep}.mp4')
            subprocess.Popen(
                f'ffmpeg -allowed_extensions ALL -protocol_whitelist http,https,tls,rtp,tcp,udp,crypto,httpproxy,file -y -i {self.dramaid}-eps-{self.ep}_1080p.m3u8 -c copy \"{output}\"', shell=True, stderr=subprocess.PIPE).communicate()

            if not os.path.exists(output):
                print('下載失敗')
                return

            if self.subtitle:
                sub = session.get(self.subtitle)
                print('正在下載字幕')
                with open(f'{self.dramaname}-E{self.ep}.vtt', 'w', encoding='utf-8') as f:
                    f.write(sub.text)

            os.remove(f'{self.dramaid}-eps-{self.ep}_1080p.m3u8')
            os.remove('m3u8.key')

    class Behind():
        def __init__(self, url):
            print('正在下載...')
            video = session.get(url)
            videoname = url.split('/')[-1]

            with open(videoname, 'wb') as f:
                f.write(video.content)

            if not os.path.exists(videoname):
                print('下載失敗')
            else:
                print('下載成功')
