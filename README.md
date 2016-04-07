# blog-with-flask  
  
[我也有个人博客啦ヾ (o ° ω ° O ) ノ゙点击进入](https://zhaowenyi.herokuapp.com/)  
  
## 说明  
部署在 Heroku 上的，打开略慢(服务器都在国外)。  
  
站内阅读不需要登陆，如果要在博文下(截止20160407还没有- -)发表评论还有将来 LAB 里可能有的东西，需要注册后登陆。  
  
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
 
  
