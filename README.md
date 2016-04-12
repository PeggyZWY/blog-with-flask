# blog-with-flask  
  
[我也有个人博客啦ヾ (o ° ω ° O ) ノ゙点击进入](https://peggyzwy.herokuapp.com/)  
  
扫一扫二维码配合手机食用也不错哦~  
![QR_Code_for_website](QR_Code_for_website.png)  
  
## 说明  
部署在 Heroku 上的，打开略慢(服务器都在国外)。  
  
站内阅读不需要登陆，如果要在博文下发表评论还有将来 LAB 里可能有的东西，需要注册后登陆。  
  
但是 QQ 邮箱的第三方授权码总是很奇怪，有时能用有时又不能，所以**找回密码**有时也不会给你发邮件，所以最好还是记住密码。万一真忘了然后找回密码那边又不给你自动发邮件，请给我直接发邮件来提醒我。  
  
## 有用的参考  
由于你懂的原因，部署时是需要 FQ 的。(访问倒是不要 FQ，未来说不准。)  
部署的时候开了 Lantern 还不行。所以如果你遇到了同样的问题，请这样解决：  
  
    $ cd ~/.ssh  
    $ vim config  
      
然后在  config 文件里写入：  
> Host heroku.com  
> User \<yourName\>  
> Hostname 107.21.95.3  
> PreferredAuthentications publickey  
> IdentityFile ~/.ssh/id_rsa  
> port 22  
 
  
## 2016-04-13 更新  
昨天发了第一篇博文[《Flask Web 遇到的问题总结》](https://peggyzwy.herokuapp.com/post/1)后发现了很多问题：  
  
1. 自动分类并没有，而且可以发现数据库里并没有存入自己填的分类  
2. 评论后跳转的?page=-1有问题
3. 除开上面的问题后，评论提交后也没有反应  
4. 新增加了统计阅读次数的功能。本地测试没问题，上线后又没有增加，就停在1了  

第2个问题解决是把这个查询给删掉了- - 
    
另外3个问题发现竟然是数据库没有提交的问题！  
这是为什么呢？config.py 里已经设置了自动提交，而且本地测试（包括第2个问题的）都完全是好好的。  
  
最后强行在每个数据库事务(add 或 delete)后加上了`db.session.commit()`，解决了以上问题。但原因还得再查查。