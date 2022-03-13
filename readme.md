<h1 align="center">LineTV-DL</h1>
簡易的LineTV下載工具

# 注意
本下載工具需要ffmpeg，請事先將ffmpeg放入系統PATH或放在資料夾裡

# 特色
免登入、免VIP直接下載1080p

（若影片是VIP會員限定的，需要登入帳號才可以下載）

CC字幕自動抓取（可開關）

# 使用方法
## 登入帳號
```
請先將config.template.json重新命名為config.json
1. 在網頁版登入好帳號後
2. 從cookies提取access_token
3. 複製到config.json裡
```
![]('https://raw.githubusercontent.com/kirbyloco/LineTV-DL/master/img/cookies.png')

## 使用者模式
直接輸入以下指令即可開始下載
```
python Linetv.py --dramaid <Dramaid> --ep <集數> --sub
# 範例
python Linetv.py --dramaid 12102 --ep 1 --sub ## 下載第一集
python Linetv.py --dramaid 12102 --epall --sub ## 下載全部集數
python Linetv.py --dramaid 12102 --ep 15-18 --sub ## 只下載15到18集
python Linetv.py --dramaid 12102 --ep 15,18 --sub ## 只下載15和17集
```
詳細參數
|指令|短指令|用途|
|-|-|-|
|--dramaid|-id|指定要下載的dramaid|
|--ep||指定要下載的集數|
|--epall||一次下載全部集數|
|--special|-sp|一次下載全部幕後花絮和精華|
|--sub||開啟字幕下載|
|--lng||輸入音軌語言（輸入ISO 639-2標準代碼）|
|--no_download||僅下載m3u8和key|

## 開發者模式
```
import Linetv # 匯入模組

parser = Linetv.Parser('輸入在Line TV看到的ID')
parser.eps ## 得到上架的集數
parser.behind() ## 得到幕後花絮相關的地址

Linetv.DL.Drama('輸入影集的ID', '影集的集數') # 只會下載一集
Linetv.DL.Behind('輸入parser.behind回傳的網址') # 下載幕後花絮用
```

