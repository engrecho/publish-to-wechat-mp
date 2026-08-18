# -*- coding: utf-8 -*-
"""Generate 公众号 HTML (红白色系) for the Atlas article."""
import html, re, os

ROOT = '/workspace/gzh_article'
OUT = os.path.join(ROOT, 'article_排版_红白色系(red-white).html')

FONT = "-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif"

def esc(t):
    return html.escape(t, quote=False)

def fix_quotes(s):
    # convert ASCII straight quotes to Chinese curly (validator flags ASCII quotes in CJK text)
    it = iter(['“', '”'])
    s = re.sub(r'"', lambda m: next(it, '”'), s)
    it2 = iter(['‘', '’'])
    s = re.sub(r"'", lambda m: next(it2, '’'), s)
    return s

def leaf(text):
    return f'<span leaf="">{esc(text)}</span>'

def para(text, underlines=None):
    """正文段落，可选淡粉下划线标记 (组件6/7d)。"""
    text = fix_quotes(text)
    if not underlines:
        return f'<p style="margin-bottom:20px;font-size:15px;line-height:1.8;text-align:justify;">{leaf(text)}</p>'
    phrases = [fix_quotes(p) for p in underlines]
    positions = []
    for ph in phrases:
        idx = text.find(ph)
        if idx != -1:
            positions.append((idx, idx + len(ph), ph))
    positions.sort()
    out, last = '', 0
    for s, e, ph in positions:
        if s < last:
            continue
        if s > last:
            out += leaf(text[last:s])
        out += f'<span style="border-bottom:2px solid #FECACA;font-weight:600;">{leaf(text[s:e])}</span>'
        last = e
    if last < len(text):
        out += leaf(text[last:])
    return f'<p style="margin-bottom:20px;font-size:15px;line-height:1.8;text-align:justify;">{out}</p>'

def section(inner, style=''):
    return f'<section style="{style}">{inner}</section>'

def chapter_header(num, en, title, first=False):
    mt = '16px' if first else '48px'
    n = num  # '01'..'05' or '∞'
    return f'''<section style="margin-top:{mt};margin-bottom:28px;padding:0 10px;">
  <section style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;padding-bottom:14px;border-bottom:3px solid #DC2626;">
    <section style="display:flex;align-items:center;">
      <span style="display:inline-block;background:#DC2626;color:#FFFFFF;font-size:18px;font-weight:900;padding:4px 14px;border-radius:6px;margin-right:14px;line-height:1.3;"><span leaf="">{n}</span></span>
      <section>
        <p style="font-size:10px;color:#DC2626;font-weight:700;letter-spacing:3px;margin:0 0 2px;text-transform:uppercase;"><span leaf="">{esc(en)}</span></p>
        <h3 style="font-size:18px;font-weight:800;color:#1C1917;margin:0;letter-spacing:0.5px;"><span leaf="">{esc(title)}</span></h3>
      </section>
    </section>
  </section>
</section>'''

def subtitle(text):
    return f'<p style="font-size:15px;font-weight:800;color:#1C1917;margin:28px 0 14px;padding-left:10px;border-left:3px solid #DC2626;line-height:1.4;"><span leaf="">{esc(fix_quotes(text))}</span></p>'

def img(path, caption=None):
    card = f'''<section style="background:#FFF;border-radius:12px;padding:6px;border:1px solid #E5E7EB;box-shadow:0 4px 12px -2px rgba(0,0,0,0.08);margin-bottom:10px;">
  <section style="margin:0;border-radius:8px;overflow:hidden;">
    <span leaf=""><img src="{path}" style="max-width:100%;height:auto;display:block;margin:0 auto;"></span>
  </section>
</section>'''
    if caption:
        card += f'<p style="font-size:12px;color:#9CA3AF;text-align:center;margin:0 0 24px;"><span leaf="">— {esc(caption)}</span></p>'
    return card

def quote8a(text):
    return f'''<section style="background:#FEF2F2;border-radius:0 10px 10px 0;border-left:4px solid #DC2626;padding:18px 22px;margin-bottom:24px;">
  <p style="font-size:16px;font-weight:800;color:#991B1B;margin:0;line-height:1.8;"><span leaf="">「{esc(fix_quotes(text))}」</span></p>
</section>'''

def quote8b(text):
    return f'''<section style="background:#FEF2F2;border-radius:10px;padding:18px 20px;margin-bottom:24px;border:1px solid #FECACA;">
  <p style="font-size:15px;color:#374151;margin:0;line-height:1.8;text-align:justify;">{leaf(fix_quotes(text))}</p>
</section>'''

def quote8d(text):
    return f'''<p style="font-size:15px;margin:0 0 24px;text-align:center;color:#DC2626;font-weight:700;letter-spacing:1px;border-top:1px solid #FEE2E2;border-bottom:1px solid #FEE2E2;padding:14px 10px;"><span leaf="">{esc(fix_quotes(text))}</span></p>'''

def intro_card(h1, m1, h2, m2, author):
    author_line = _intro_author(author)
    return f'''<section style="margin:10px 10px 32px;background:#ffffff;border-radius:12px;box-shadow:0 4px 24px -4px rgba(220,38,38,0.15);padding:28px 24px 22px;overflow:hidden;">
  <p style="font-size:42px;color:#DC2626;font-weight:900;margin:0;line-height:0.6;"><span leaf="">“</span></p>
  <p style="font-size:16px;font-weight:800;color:#1C1917;margin:12px 0 8px;line-height:1.75;padding-left:4px;">
    <span style="background:#DC2626;color:#FFFFFF;padding:2px 8px;border-radius:4px;"><span leaf="">{esc(h1)}</span></span>
    <span leaf="">{esc(m1)}</span>
    <span style="background:#DC2626;color:#FFFFFF;padding:2px 8px;border-radius:4px;"><span leaf="">{esc(h2)}</span></span>
    <span leaf="">{esc(m2)}</span>
  </p>
  {author_line}
</section>'''

def _intro_author(author):
    if not author:
        return ''
    return f'<p style="text-align:right;font-size:12px;color:#9CA3AF;margin:8px 0 0;letter-spacing:1px;"><span leaf="">—— {esc(author)}</span></p>'

def toc(items):
    cards = ''
    for i, (n, t) in enumerate(items):
        mr = '8px' if i < 2 else '0'
        cards += f'''<section style="flex:1;background:#FEF2F2;border-radius:10px;padding:16px 12px;margin-right:{mr};text-align:center;border:1px solid #FEE2E2;">
      <p style="display:inline-block;background:#DC2626;color:#FFFFFF;font-size:12px;font-weight:800;padding:2px 10px;border-radius:4px;margin:0 0 8px;"><span leaf="">{n}</span></p>
      <p style="font-size:13px;font-weight:700;color:#1C1917;margin:0;"><span leaf="">{esc(t)}</span></p>
    </section>'''
    return f'''<section style="padding:0 10px 32px;">
  <p style="font-size:14px;color:#9CA3AF;margin:0 0 14px;letter-spacing:1px;"><span leaf="">📌 本文看点</span></p>
  <section style="display:flex;justify-content:space-between;">{cards}</section>
</section>'''

def divider():
    return '''<section style="padding:0 10px;">
  <section style="height:1px;background:linear-gradient(to right,transparent,#FCA5A5,#DC2626,#FCA5A5,transparent);margin:0;"><span leaf=""><br></span></section>
</section>'''

def end_line():
    return '''<section style="padding:0 10px;">
  <section style="text-align:center;margin:0 0 32px;">
    <section style="display:flex;align-items:center;justify-content:center;">
      <span style="height:2px;width:60px;background:linear-gradient(to right,transparent,#DC2626);margin-right:12px;"><span leaf=""><br></span></span>
      <span style="font-size:11px;color:#DC2626;letter-spacing:3px;font-weight:700;"><span leaf="">END</span></span>
      <span style="height:2px;width:60px;background:linear-gradient(to left,transparent,#DC2626);margin-left:12px;"><span leaf=""><br></span></span>
    </section>
  </section>
</section>'''

def sign(card_img, line1, cta):
    card = ''
    if card_img:
        card = f'''<section style="text-align:center;margin-bottom:10px;border-radius:12px;overflow:hidden;">
    <span leaf=""><img src="{card_img}" style="max-width:100%;height:auto;display:block;margin:0 auto;"></span>
  </section>'''
    return f'''<section style="padding:0 10px;">
  {card}
  <p style="margin-bottom:20px;font-size:15px;line-height:1.8;text-align:justify;"><span leaf="">{esc(fix_quotes(line1))}</span></p>
  <p style="margin-bottom:20px;font-size:15px;line-height:1.8;text-align:justify;">
    <span leaf="">如果你觉得今天这篇有收获，欢迎</span>
    <strong style="color:#DC2626;"><span leaf="">点赞、在看、转发</span></strong>
    <span leaf="">{esc(cta)}</span>
  </p>
</section>'''

# ============================ ASSEMBLE ============================
parts = []
parts.append(f'<section style="max-width:677px;margin:0 auto;background:#ffffff;font-family:{FONT};color:#374151;line-height:1.75;letter-spacing:0.5px;overflow-x:hidden;">')

# 1. 引言卡
parts.append(intro_card(
    "对话本身", "就能完成搜索、阅读与整理，", "独立的AI浏览器", "就成了多余的中间层。", ""))

# 2. 前言正文
parts.append('<section style="padding:0 10px;">')
parts.append(para(
    "OpenAI宣布关停Atlas——这款上线不到一年的AI浏览器，死于ChatGPT自己。当ChatGPT的搜索足够精准、引用足够可靠，用户不再需要「先打开AI浏览器再让AI帮忙」；原本需要浏览器完成的工作，直接在对话里就能解决。",
    ["死于ChatGPT自己", "直接在对话里就能解决"]))
parts.append('</section>')

# 3. 导读
parts.append(toc([
    ("01", "Atlas为何死于ChatGPT"),
    ("02", "流量入口被AI改写"),
    ("03", "浏览器永存，AI浏览器退场"),
]))

# 4. 第一章
parts.append(chapter_header("01", "SHUTDOWN", "OpenAI放弃了自己的AI浏览器", first=True))
parts.append('<section style="padding:0 10px;">')
parts.append(para(
    "根据OpenAI官方文档，Atlas将于2026年8月9日停止运行。用户需要提前迁移想保留的数据，包括书签、打开的标签页和浏览历史记录，均不会自动转移。",
    ["2026年8月9日停止运行", "均不会自动转移"]))
parts.append(img("images/img01.jpg"))
parts.append(para(
    "这款浏览器于2025年10月上线，从发布到停止服务，生命周期不到一年。",
    ["生命周期不到一年"]))
parts.append(quote8a("Atlas死于ChatGPT。OpenAI已经意识到，AI浏览器注定没有未来。"))
parts.append(img("images/img02.jpg"))
parts.append('</section>')

# 5. 第二章
parts.append(divider())
parts.append(chapter_header("02", "CONTEXT", "Atlas，死于ChatGPT"))
parts.append('<section style="padding:0 10px;">')
parts.append(para(
    "去年10月，在Atlas出现的时候，AI浏览器有非常充分的存在理由。",
    ["非常充分的存在理由"]))
parts.append(para(
    "OpenAI推出ChatGPT Atlas时，给它的定义是「一款以ChatGPT为核心内置的全新网络浏览器」。",
    ["以ChatGPT为核心内置"]))
parts.append(img("images/img03.jpg"))
parts.append(para(
    "但OpenAI认为，搜索只是第一步。浏览器才是汇聚各项工作、工具和背景信息的核心之地。",
    ["浏览器才是汇聚各项工作、工具和背景信息的核心之地"]))
parts.append(para(
    "于是，一个自然的想法出现了：如果AI未来要替用户完成任务，浏览器可能会成为Agent进入互联网的工作空间。",
    ["Agent进入互联网的工作空间"]))
parts.append(para(
    "这个方向并不是OpenAI独有的判断，在那段时间里，OpenAI甚至算得上「后来者」。",
    ["甚至算得上后来者"]))
parts.append(subtitle("其他玩家相继入局"))
parts.append(para(
    "2025年初，The Browser Company推出了AI浏览器Dia。相比传统浏览器，Dia将AI能力直接融入浏览流程，用户可以让AI理解当前标签页内容、总结信息、生成文本，并基于浏览上下文完成任务。",
    ["将AI能力直接融入浏览流程"]))
parts.append(para(
    "2025年上半年进入公众视野的Fellou则进一步押注AI浏览器方向，希望让AI不仅阅读网页，还能够规划任务、跨网站执行操作，把浏览器从信息查看工具变成任务执行环境。",
    ["跨网站执行操作"]))
parts.append(para(
    "随后，2025年7月，Perplexity推出Comet，同样试图把AI搜索、网页理解和Agent能力融合进浏览器。",
    ["融合进浏览器"]))
parts.append(para(
    "包括Atlas在内，这些AI浏览器产品有一个共同的判断：过去，浏览器是人进入互联网的入口；未来，浏览器可能成为AI进入互联网的入口。",
    ["浏览器可能成为AI进入互联网的入口"]))
parts.append(quote8a("这个判断本身可能并没有出错，但在不到一年之后，OpenAI改变了答案。"))
parts.append('</section>')

# 6. 第三章
parts.append(divider())
parts.append(chapter_header("03", "TRAFFIC", "流量分配方式，正在被AI改写"))
parts.append('<section style="padding:0 10px;">')
parts.append(para(
    "OpenAI最终保留了Atlas探索出的能力，说明浏览器Agent的价值仍然存在。但与此同时，另一件事正在发生：AI正在改变搜索时代形成的流量分配方式。",
    ["AI正在改变搜索时代形成的流量分配方式"]))
parts.append(para(
    "Search Engine Land援引Previsible发布的AI Traffic Study称，研究团队分析了677万次LLM驱动的网站访问，发现截至2026年5月，LLM带来的月访问量达到64.4万次，相比此前增长9.9倍。其中，ChatGPT贡献了92.4%的AI推荐流量。",
    ["增长9.9倍", "92.4%的AI推荐流量"]))
parts.append(img("images/img04.jpg"))
parts.append(para(
    "与此同时，Search Engine Land援引Chartbeat Analytics数据称，基于数千家全球网站的流量分析，小型出版商过去两年来自搜索引擎的推荐流量下降60%，中型出版商下降47%；同期，Google Search带来的页面浏览量下降34%，而ChatGPT推荐流量增长超过200%。",
    ["下降60%", "增长超过200%"]))
parts.append(img("images/img05.jpg"))
parts.append(para(
    "虽然ChatGPT推荐流量目前仍占不到网站总流量的1%，但这些变化已经说明，AI正在成为新的流量入口。",
    ["AI正在成为新的流量入口"]))
parts.append(quote8b(
    "以我自己的经历作为举例，曾经有一段时间，Perplexity的Comet是我的默认浏览器。当时我经常用它搜索事件的相关报道，尤其用来查找原始信源——AI幻觉是一个很大的风险，我必须找到原始链接去核实才能安心。但后来，随着ChatGPT的搜索能力不断增强，我几乎再也没有打开过Comet，默认浏览器也换回了Chrome。"))
parts.append(para(
    "Comet并没有变差，但ChatGPT逐渐补齐了我最关心的价值：搜索更准确，引用来源更可靠，链接与回答之间的对应关系更稳定，复杂资料整理也可以直接在对话中完成。",
    ["搜索更准确，引用来源更可靠"]))
parts.append(para(
    "或者说，那些原本需要通过AI浏览器完成的工作，现在已经可以直接在Chatbot中完成。",
    ["直接在Chatbot中完成"]))
parts.append(para(
    "在国内，许多人在遇到问题时，也越来越多地打开豆包和DeepSeek（并开启智能搜索），而不像过去那样「百度一下」。",
    ["豆包和DeepSeek", "百度一下"]))
parts.append('</section>')

# 7. 第四章
parts.append(divider())
parts.append(chapter_header("04", "RETHINK", "AI浏览器没有未来，但浏览器不会没有AI"))
parts.append('<section style="padding:0 10px;">')
parts.append(para(
    "Atlas死于ChatGPT，死因就在这里。死去的不是浏览器Agent这一方向，而是决定AI浏览器是否必要的假设：用户是否需要先打开一款AI浏览器，再让AI帮助自己使用互联网。",
    ["死去的不是浏览器Agent这一方向"]))
parts.append(para(
    "随着AI逐渐具备独立完成搜索、理解网页和执行任务的能力，OpenAI给出的答案是否定的。",
    ["OpenAI给出的答案是否定的"]))
parts.append(para(
    "OpenAI放弃Atlas，其实也和公司的整体路线有关。Atlas最初想成为ChatGPT进入互联网的入口，但今天的OpenAI正在推动ChatGPT成为更大的统一入口。",
    ["推动ChatGPT成为更大的统一入口"]))
parts.append(quote8d("OpenAI需要的是一个超级助手，而不是一个超级助手旁边再放一个浏览器。"))
parts.append(subtitle("两个容易混淆的概念"))
parts.append(para(
    "在对此展开讨论之前，我们需要区分一个容易混淆的概念：AI浏览器，和浏览器+AI。它们看起来相似，但实际上代表两条不同路线。",
    ["AI浏览器，和浏览器+AI"]))
parts.append(para(
    "AI浏览器试图创造一个新的入口，把浏览器从「网页查看器」，变成一个能够理解目标、调用网页并执行任务的Agent，因此也需要用户完成一次迁移，放弃已经使用多年的浏览器，改用一个新的产品。",
    ["创造一个新的入口"]))
parts.append(para(
    "浏览器+AI则是另一条路线，它并不要求用户改变入口，而是在已有的浏览器中加入AI能力。对于用户来说，这种变化更加自然，因为浏览器本身已经积累了大量无法轻易替代的资产：收藏夹、历史记录、密码、插件、登录状态，以及长期形成的使用习惯。",
    ["并不要求用户改变入口"]))
parts.append(para(
    "拿国内的几家产品举例，美团的Tabbit更接近Perplexity的Comet（以及OpenAI将被关停的Atlas），算是原生的「AI浏览器」，也因此更容易和通用Agent发生重叠。",
    ["美团的Tabbit"]))
parts.append(para(
    "而腾讯的QQ浏览器、阿里的夸克浏览器和360浏览器，虽然都称自己是「AI浏览器」，但这三个产品本质上更接近「浏览器+AI」——它们本来就有浏览器，只是在自己原有的浏览器里加上AI能力。",
    ["本质上更接近浏览器+AI"]))
parts.append(para(
    "浏览器+AI这条路线的代表是谷歌，它的逻辑很容易理解：Chrome已经是数十亿用户访问互联网的入口，谷歌完全没有必要放弃自己的历史积累，重新创造一个入口。",
    ["谷歌完全没有必要放弃自己的历史积累"]))
parts.append(para(
    "2025年，谷歌开始将Gemini能力逐步整合进Chrome，包括AI模式、页面理解、跨标签页辅助、浏览历史问答，以及基于浏览器上下文的任务帮助。",
    ["将Gemini能力逐步整合进Chrome"]))
parts.append(para(
    "我们不妨认为，AI浏览器这个产品形态本身可能就是一个过渡阶段。因为AI需要浏览器，和用户需要AI浏览器，本质上并不是一回事。",
    ["AI浏览器这个产品形态本身可能就是一个过渡阶段"]))
parts.append(para(
    "真正有价值的并不是「AI浏览器」这一产品形态，而是浏览器能力本身。",
    ["浏览器能力本身"]))
parts.append('</section>')

# 8. 第五章（结语 ∞）
parts.append(divider())
parts.append(chapter_header("∞", "THE END", "Atlas关停，而浏览器永存"))
parts.append('<section style="padding:0 10px;">')
parts.append(para(
    "「AI浏览器」失去价值，并不代表浏览器本身失去价值。",
    ["并不代表浏览器本身失去价值"]))
parts.append(para(
    "AI改变的是浏览器作为搜索入口的角色，而不是浏览器作为互联网分发入口的价值。",
    ["作为互联网分发入口的价值"]))
parts.append(para(
    "过去，浏览器和搜索引擎共同构成了互联网最重要的信息分发链路：用户打开浏览器，通过搜索引擎寻找信息，再进入网站获取内容。而AI正在改变这套模式，用户不再需要访问十几个网页，可以让AI搜索、阅读、整理多个来源，直接生成答案。",
    ["直接生成答案"]))
parts.append(para(
    "但搜索只是互联网分发的一部分，互联网本身并不会消失。大量服务仍然运行在网页里：电商平台、企业软件、金融服务、内容网站、数据库，以及各种在线工具。",
    ["互联网本身并不会消失"]))
parts.append(para(
    "即使——理想情况下，未来大部分信息获取由AI完成，但用户依然需要访问互联网中的各种服务。",
    ["用户依然需要访问互联网中的各种服务"]))
parts.append(para(
    "并且，AI本身也需要这些服务、需要互联网和浏览器。",
    ["AI本身也需要这些服务"]))
parts.append(quote8a("某种意义上，浏览器之于知识工作Agent，就像终端之于编程Agent。"))
parts.append(para(
    "Codex和Claude Code需要终端环境，不代表未来需要一个AI终端。终端的价值在于它提供了代码、文件、运行环境和项目状态。同样，浏览器的价值也在于它提供了网页、账户、服务、操作界面，以及AI时代最珍贵的一类资产——上下文。",
    ["AI时代最珍贵的一类资产——上下文"]))
parts.append(para(
    "用户正在阅读哪篇文章，打开了哪些标签页，搜索过什么内容，正在使用哪些网站，这些信息共同构成了用户真实的工作状态。对于Agent来说，这些上下文非常重要。",
    ["这些上下文非常重要"]))
parts.append(para(
    "所以，拥有传统互联网入口的公司并没有因为AI崛起而放弃浏览器，而是在用AI改造浏览器。",
    ["用AI改造浏览器"]))
parts.append(para(
    "浏览器作为互联网分发基础设施的价值仍在，它不只是一个网页查看工具，更是AI时代用户、内容、服务和商业之间的连接方式。",
    ["用户、内容、服务和商业之间的连接方式"]))
parts.append(para(
    "AI时代的浏览器之争，早已不只是争夺搜索入口。它们争夺的是用户互联网活动的上下文入口、跨网站执行任务的权限、AI与用户之间最高频的交互界面，以及未来搜索、购物、广告和交易的分发权。",
    ["上下文入口", "最高频的交互界面"]))
parts.append('</section>')

# 9. END（之后不再附加署名/来源，按用户要求删除 END 之后全部内容）
parts.append(end_line())

# 10. 末尾用户提供的图片
parts.append('<section style="padding:0 10px;margin-bottom:20px;">')
parts.append(img("images/img_end.jpg"))
parts.append('</section>')

parts.append('</section>')  # close global container

html_out = '\n'.join(parts)
open(OUT, 'w', encoding='utf-8').write(html_out)
print("WROTE", OUT, len(html_out), "bytes")

# 自动重新生成预览页 + 刷新本地服务入口，避免「改了内容预览没变」
import subprocess
PREVIEW = OUT[:-5] + "_预览.html"
SKILL_WRAP = "/root/.codebuddy/skills/gzh-design/scripts/wrap_preview.py"
try:
    subprocess.run(["python3.11", SKILL_WRAP, OUT], check=True)
    subprocess.run(["cp", PREVIEW, os.path.join(ROOT, "index.html")], check=True)
    print("PREVIEW refreshed -> index.html (live server updated)")
except Exception as e:
    print("WARN: preview refresh failed:", e)
