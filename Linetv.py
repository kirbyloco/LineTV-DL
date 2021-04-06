import os
import re
import subprocess

import requests
from lxml import etree


class Parser():
    def __init__(self, dramaid):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'
        })
        self.dramaid = str(dramaid)
        self.eps = []
        self.get_eps()
        if self.eps:
            self.failed = False
        else:
            self.failed = True

    def get_eps(self):
        req = self.session.get(f'https://www.linetv.tw/drama/{self.dramaid}')
        parser = etree.HTML(req.text)
        for _ in parser.xpath('//li/a/h3'):
            self.eps.append(re.findall(r'(\d+)', _.text)[0])


class DL():
    def __init__(self, dramaid: str, ep: str):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'
        })
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
        req = self.session.get(
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
        req = self.session.post(
            'https://www.linetv.tw/api/part/dinosaurKeeper', data=data)
        token = req.json()['token']
        key = self.session.get(
            'https://keydeliver.linetv.tw/jurassicPark', headers={'authentication': token})
        with open(os.path.join('.', 'm3u8.key'), 'wb') as f:
            f.write(key.content)

    def dl_video(self):
        urlfix = re.findall(r'(.*\/)\d+.*\d', self.m3u8)[0]
        m3u8url = f'{urlfix}1080/{self.dramaid}-eps-{self.ep}_1080p.m3u8'
        m3u8 = self.session.get(m3u8url)
        m3u8 = re.sub(r'https://keydeliver.linetv.tw/jurassicPark',
                      'm3u8.key', m3u8.text)
        m3u8 = re.sub(f'{self.dramaid}-eps-{self.ep}_1080p.ts',
                      f'{urlfix}1080/{self.dramaid}-eps-{self.ep}_1080p.ts', m3u8)
        with open(os.path.join('.', f'{self.dramaid}-eps-{self.ep}_1080p.m3u8'), 'w') as f:
            f.write(m3u8)
        # 保留程式碼
        # videourl = f'{urlfix}1080/{self.dramaid}-eps-{self.ep}_1080p.ts'
        # video = self.session.get(videourl)
        # with open(os.path.join('.', f'{self.dramaid}-eps-{self.ep}_1080p.ts'), 'wb') as f:
        #     f.write(video.content)
        print(f'正在下載：{self.dramaname} 第{self.ep}集')
        output = os.path.join('.', f'{self.dramaname}-E{self.ep}.mp4')
        subprocess.Popen(
            f'ffmpeg -allowed_extensions ALL -protocol_whitelist http,https,tls,rtp,tcp,udp,crypto,httpproxy,file -y -i {self.dramaid}-eps-{self.ep}_1080p.m3u8 -c copy \"{output}\"', shell=True, stderr=subprocess.PIPE).communicate()
        if not os.path.exists(output):
            print('下載失敗')
            return
        if self.subtitle:
            sub = self.session.get(self.subtitle)
            print('正在下載字幕')
            with open(f'{self.dramaname}-E{self.ep}.vtt', 'w', encoding='utf-8') as f:
                f.write(sub.text)
        os.remove(f'{self.dramaid}-eps-{self.ep}_1080p.m3u8')
        os.remove('m3u8.key')
