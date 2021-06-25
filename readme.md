<h1 align="center">LineTV-DL</h1>
簡易的LineTV下載工具

# 注意
本下載工具需要ffmpeg，請事先將ffmpeg放入系統PATH或放在資料夾裡

# 特色
免登入、免VIP直接下載1080p

（若影片是VIP會員限定的，則不能下載）

CC字幕自動抓取

# 使用方法
## 登入帳號
```
請先將config.template.json重新命名為config.json
1. 在網頁版登入好帳號後
2. 從cookies提取access_token
3. 複製到config.json裡
```
![]('https://raw.githubusercontent.com/kirbyloco/LineTV-DL/master/img/cookies.png')
## 匯入模組
```
import Linetv # 匯入模組
```
## 解析影集
```
parser = Linetv.Parser('輸入在Line TV看到的ID')
parser.eps ## 得到上架的集數
parser.behind() ## 得到幕後花絮相關的地址
```
## 下載影集
```
Linetv.DL.Drama('輸入影集的ID', '影集的集數') # 只會下載一集
Linetv.DL.Behind('輸入parser.behind回傳的網址') # 下載幕後花絮用
```

