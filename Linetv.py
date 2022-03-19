import json
import os
import re
import subprocess

import requests
from lxml import etree

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
session = requests.Session()
session.headers.update({'User-Agent': UA})

try:
    with open('config.json') as f:
        config = json.load(f)
    if config['access_token']:
        session.headers.update({'authorization': config['access_token']})
except:
    print('找不到config.json，將採用未登入模式下載')


class Parser():
    def __init__(self, dramaid: str):
        self.dramaid = str(dramaid)
        self.html = session.get(f'https://www.linetv.tw/drama/{self.dramaid}')
        self.get_eps()
        self.get_behind()

    def get_eps(self):
        self.eps = []
        parser = etree.HTML(self.html.text)
        data = json.loads(parser.xpath('//head/script')[0].text[27:])
        for _ in data['entities']['dramaInfo']['byId'][self.dramaid]['eps_info']:
            self.eps.append(_['number'])

    def get_behind(self):
        self.behind = {}
        parser = etree.HTML(self.html.text)
        data = json.loads(parser.xpath(
            '//script[@type="application/ld+json"]')[2].text)
        for _trailer in data['trailer']:
            self.behind[_trailer['name']] = _trailer['contentUrl']


class DL:
    class Drama():
        def __init__(self, dramaid: str, ep: str, lng: str, subtitle=False, no_download=False):
            self.dramaid = dramaid
            self.subtitle = subtitle
            self.ep = ep
            self.lng = lng
            self.no_download = no_download
            self.dramaname = ''
            self.keyId = ''
            self.keyType = ''
            self.m3u8 = ''
            self.sub_url = ''
            self.urlfix = ''
            self.res = '1080p'
            self.check_ffmpeg()
            self.get_part_url()
            self.get_m3u8()
            self.get_m3u8_key()
            self.dl_video()
            # shutil.rmtree('.')

        def check_ffmpeg(self):
            try:
                subprocess.Popen(
                    'ffmpeg -h', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except FileNotFoundError:
                print('本項目需要ffmpeg，請手動安裝ffmpeg')
                raise

        def get_part_url(self):
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
                self.sub_url = parser['subtitle']

        def get_m3u8(self):
            self.urlfix = re.findall(r'(.*\/)\d+.*\d', self.m3u8)[0]
            req = session.get(self.m3u8)
            res = re.findall(r'(\d*\/\d*-eps-\d*_\d*p.m3u8)', req.text)
            if res:
                self.res = '1080'
                m3u8url = f'{self.urlfix}1080/{self.dramaid}-eps-{self.ep}_1080p.m3u8'
                m3u8 = session.get(m3u8url)
                m3u8 = re.sub(r'https://keydeliver.linetv.tw/jurassicPark',
                              f'{self.dramaid}-eps-{self.ep}_1080p.key', m3u8.text)
                m3u8 = re.sub(f'{self.dramaid}-eps-{self.ep}_1080p.ts',
                              f'{self.urlfix}1080/{self.dramaid}-eps-{self.ep}_1080p.ts', m3u8)
                with open(os.path.join('.', f'{self.dramaid}-eps-{self.ep}_1080p.m3u8'), 'w') as f:
                    f.write(m3u8)
            else:
                self.res = '480'
                res = re.findall(r'(\d*-eps-\d*_\d*p_\.m3u8)', req.text)
                m3u8url = f'{self.urlfix}{self.dramaid}-eps-{self.ep}_480p_.m3u8'
                m3u8 = session.get(m3u8url)
                m3u8 = re.sub(r'https://keydeliver.linetv.tw/jurassicPark',
                              f'{self.dramaid}-eps-{self.ep}_480p.key', m3u8.text)
                m3u8 = re.sub(r'(\d*-eps-\d*_\d*p_\d*\.ts)',
                              r'{}\1'.format(self.urlfix), m3u8)
                with open(os.path.join('.', f'{self.dramaid}-eps-{self.ep}_480p.m3u8'), 'w') as f:
                    f.write(m3u8)

        def get_m3u8_key(self):
            data = {'keyType': self.keyType, 'keyId': self.keyId,
                    'dramaId': int(self.dramaid), 'eps': int(self.ep)}
            req = session.post(
                'https://www.linetv.tw/api/part/dinosaurKeeper', json=data)
            token = req.json()['token']
            key = requests.get(
                'https://keydeliver.linetv.tw/jurassicPark', headers={'authentication': token})
            with open(os.path.join('.', f'{self.dramaid}-eps-{self.ep}_{self.res}p.key'), 'wb') as f:
                f.write(key.content)

        def dl_video(self):
            if self.no_download:
                return

            print(f'正在下載：{self.dramaname} 第{self.ep}集')
            output = os.path.join('.', f'{self.dramaname}-E{self.ep}.mp4')
            ffmpeg_cmd = ['ffmpeg', '-loglevel', 'quiet', '-stats', '-allowed_extensions', 'ALL',
                          '-protocol_whitelist', 'http,https,tls,rtp,tcp,udp,crypto,httpproxy,file', '-y', '-i', f'{self.dramaid}-eps-{self.ep}_{self.res}p.m3u8', '-movflags', '+faststart', '-c', 'copy']

            if self.lng:
                ffmpeg_cmd.extend(['-metadata:s:a:0', f'language={self.lng}'])
            ffmpeg_cmd.extend([output])
            subprocess.Popen(
                ffmpeg_cmd, shell=False, stderr=subprocess.PIPE).communicate()

            if not os.path.exists(output):
                print('下載失敗')
                return
            else:
                print('下載完成')

            if self.sub_url and self.subtitle:
                sub = session.get(self.sub_url)
                if sub.status_code != 200:
                    print('正在下載字幕')
                    sub = session.get(
                        f'{self.urlfix}caption/{self.dramaid}-eps-{self.ep}.vtt')
                with open(f'{self.dramaname}-E{self.ep}.vtt', 'w', encoding='utf-8') as f:
                    f.write(sub.text)

            os.remove(f'{self.dramaid}-eps-{self.ep}_{self.res}p.m3u8')
            os.remove(f'{self.dramaid}-eps-{self.ep}_{self.res}p.key')

    class Behind():
        def __init__(self, url: str, filename: str):
            print(f'正在下載{filename}')
            video = session.get(url)
            videoname = filename + url.split('/')[-1][-4:]

            with open(videoname, 'wb') as f:
                f.write(video.content)

            if not os.path.exists(videoname):
                print('下載失敗')
            else:
                print('下載成功')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--dramaid', '-id', help='輸入DramaId')
    parser.add_argument('--ep', help='輸入集數')
    parser.add_argument('--epall', help='一次下載全部集數', action="store_true")
    parser.add_argument('--special', '-sp',
                        help='一次下載全部幕後花絮和精華', action="store_true")
    parser.add_argument('--sub', help='若有字幕自動下載', action="store_true")
    parser.add_argument('--lng', help='輸入音軌語言')
    parser.add_argument('--no_download', help='僅下載m3u8和key',
                        action="store_true")
    args = parser.parse_args()

    if args.dramaid and args.special:
        sps = Parser(args.dramaid).behind
        for sp in sps:
            DL.Behind(sps[sp], sp)

    if args.dramaid and args.epall:
        for _ep in Parser(args.dramaid).eps:
            DL.Drama(args.dramaid, _ep, args.lng, args.sub, args.no_download)

    if args.dramaid and args.ep:
        if args.ep.find('-') != -1:
            ids = range(
                int(args.ep.split('-')[0]), int(args.ep.split('-')[1]) + 1)
        elif args.ep.find(',') != -1:
            ids = args.ep.split(',')
        else:
            ids = [args.ep]
        for _ep in ids:
            DL.Drama(args.dramaid, _ep, args.lng, args.sub, args.no_download)
