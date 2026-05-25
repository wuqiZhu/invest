# -*- coding: utf-8 -*-
"""
投研知识库模块

功能：
1. 专业投资者书籍库（全球经典书籍）
2. 名人发言追踪（演讲、社交媒体）
3. 广告/传销风险识别
4. 投资智慧金句

免责声明：
本工具仅供个人学习和研究使用，不构成任何投资建议。
"""

import json
import os
import re
from datetime import datetime


class KnowledgeBase:
    """投研知识库"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), 'knowledge_db.json')
        self.load()
    
    def load(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.books = data.get('books', [])
                self.quotes = data.get('quotes', [])
                self.warnings = data.get('warnings', [])
                self.notes = data.get('notes', [])
        else:
            self.books = self._init_books()
            self.quotes = self._init_quotes()
            self.warnings = self._init_warnings()
            self.notes = []
            self.save()
    
    def save(self):
        data = {
            'books': self.books,
            'quotes': self.quotes,
            'warnings': self.warnings,
            'notes': self.notes
        }
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _init_books(self):
        return [
            {
                "title": "The Intelligent Investor",
                "author": "Benjamin Graham",
                "year": 1949,
                "level": "经典",
                "focus": "价值投资",
                "key_points": ["安全边际", "市场先生", "防御型投资者"],
                "recommended": True
            },
            {
                "title": "A Random Walk Down Wall Street",
                "author": "Burton Malkiel",
                "year": 1973,
                "level": "入门",
                "focus": "指数投资",
                "key_points": ["有效市场假说", "随机漫步", "指数基金"],
                "recommended": True
            },
            {
                "title": "One Up On Wall Street",
                "author": "Peter Lynch",
                "year": 1989,
                "level": "进阶",
                "focus": "选股策略",
                "key_points": ["十倍股", "六种股票分类", "实地调研"],
                "recommended": True
            },
            {
                "title": "Common Stocks and Uncommon Profits",
                "author": "Philip Fisher",
                "year": 1958,
                "level": "进阶",
                "focus": "成长投资",
                "key_points": ["SCUTTLEBUTT方法", "15要点清单", "长期持有"],
                "recommended": True
            },
            {
                "title": "The Little Book of Common Sense Investing",
                "author": "John Bogle",
                "year": 2007,
                "level": "入门",
                "focus": "指数投资",
                "key_points": ["低成本", "长期投资", "复利效应"],
                "recommended": True
            },
            {
                "title": "Thinking, Fast and Slow",
                "author": "Daniel Kahneman",
                "year": 2011,
                "level": "心理学",
                "focus": "行为金融",
                "key_points": ["系统1和系统2", "损失厌恶", "锚定效应"],
                "recommended": True
            },
            {
                "title": "The Psychology of Money",
                "author": "Morgan Housel",
                "year": 2020,
                "level": "入门",
                "focus": "理财心理",
                "key_points": ["复利思维", "尾部风险", "财富与幸福"],
                "recommended": True
            },
            {
                "title": "Margin of Safety",
                "author": "Seth Klarman",
                "year": 1991,
                "level": "高级",
                "focus": "价值投资",
                "key_points": ["安全边际", "逆向投资", "风险厌恶"],
                "recommended": False
            },
            {
                "title": "穷查理宝典",
                "author": "查理·芒格",
                "year": 2005,
                "level": "进阶",
                "focus": "多元思维",
                "key_points": ["多元思维模型", "逆向思维", "能力圈"],
                "recommended": True
            },
            {
                "title": "聪明的投资者",
                "author": "本杰明·格雷厄姆",
                "year": 1949,
                "level": "经典",
                "focus": "价值投资",
                "key_points": ["安全边际", "市场先生", "防御型投资"],
                "recommended": True
            },
            {
                "title": "投资最重要的事",
                "author": "霍华德·马克斯",
                "year": 2011,
                "level": "进阶",
                "focus": "风险管理",
                "key_points": ["第二层思维", "风险控制", "市场周期"],
                "recommended": True
            },
            {
                "title": "漫步华尔街",
                "author": "伯顿·马尔基尔",
                "year": 1973,
                "level": "入门",
                "focus": "投资理论",
                "key_points": ["随机漫步", "技术分析局限", "基本面分析"],
                "recommended": True
            }
        ]
    
    def _init_quotes(self):
        return [
            {
                "author": "Warren Buffett",
                "quote": "别人贪婪时我恐惧，别人恐惧时我贪婪。",
                "context": "投资心态",
                "source": "股东信"
            },
            {
                "author": "Warren Buffett",
                "quote": "投资的第一条规则是不要亏钱，第二条规则是不要忘记第一条。",
                "context": "风险控制",
                "source": "演讲"
            },
            {
                "author": "Charlie Munger",
                "quote": "反过来想，总是反过来想。",
                "context": "逆向思维",
                "source": "演讲"
            },
            {
                "author": "Charlie Munger",
                "quote": "在有鱼的地方钓鱼。",
                "context": "选择机会",
                "source": "演讲"
            },
            {
                "author": "Peter Lynch",
                "quote": "知道你拥有什么，以及你为什么拥有它。",
                "context": "投资研究",
                "source": "书籍"
            },
            {
                "author": "Howard Marks",
                "quote": "你不能通过做和其他所有人一样的事情来取得超额收益。",
                "context": "逆向投资",
                "source": "备忘录"
            },
            {
                "author": "Howard Marks",
                "quote": "最重要的事情不是进攻，而是防守。",
                "context": "风险控制",
                "source": "备忘录"
            },
            {
                "author": "Benjamin Graham",
                "quote": "市场短期是投票机，长期是称重机。",
                "context": "市场本质",
                "source": "书籍"
            },
            {
                "author": "John Bogle",
                "quote": "不要试图在干草堆里找针，买下整个干草堆。",
                "context": "指数投资",
                "source": "书籍"
            },
            {
                "author": "George Soros",
                "quote": "重要的不是你判断对了还是错了，而是你对的时候赚了多少，错的时候亏了多少。",
                "context": "风险管理",
                "source": "书籍"
            },
            {
                "author": "Ray Dalio",
                "quote": "如果你不敢持有一只股票10年，那就不要持有它10分钟。",
                "context": "长期投资",
                "source": "书籍"
            },
            {
                "author": "李录",
                "quote": "投资的本质是对未来做出有依据的预测。",
                "context": "投资本质",
                "source": "演讲"
            },
            {
                "author": "张磊",
                "quote": "在长期主义的道路上，与伟大格局观者同行。",
                "context": "长期投资",
                "source": "书籍"
            },
            {
                "author": "投资智慧",
                "quote": "解决问题的资源最贵，能解决问题的人最有价值。",
                "context": "科技投资",
                "source": "行业洞察"
            },
            {
                "author": "投资智慧",
                "quote": "中国的很多情况可以参考日本、韩国等先服版本玩家。",
                "context": "跨市场研究",
                "source": "行业洞察"
            },
            {
                "author": "投资智慧",
                "quote": "历史不会简单重复，但会押韵。",
                "context": "历史规律",
                "source": "Mark Twain"
            }
        ]
    
    def _init_warnings(self):
        return [
            {
                "type": "广告",
                "keywords": ["保本保息", "稳赚不赔", "无风险高收益", "保证收益", "每日分红"],
                "warning": "承诺保本或固定高收益的都是骗局",
                "risk_level": "高"
            },
            {
                "type": "传销",
                "keywords": ["拉人头", "层级返利", "动态收益", "静态收益", "分享赚钱"],
                "warning": "需要发展下线的都是传销模式",
                "risk_level": "极高"
            },
            {
                "type": "诈骗",
                "keywords": ["内部消息", "主力拉升", "涨停板", "老师带单", "免费荐股"],
                "warning": "声称有内部消息或保证涨停的都是诈骗",
                "risk_level": "极高"
            },
            {
                "type": "误导",
                "keywords": ["股神", "翻倍", "暴富", "一夜暴富", "快速致富"],
                "warning": "过度承诺收益的都是误导",
                "risk_level": "中"
            },
            {
                "type": "误导",
                "keywords": ["百分百", "包赚", "必涨", "只涨不跌", "零风险"],
                "warning": "绝对化表述通常不可信",
                "risk_level": "中"
            },
            {
                "type": "庞氏",
                "keywords": ["高额回报", "短期翻倍", "资金盘", "互助盘", "拆分盘"],
                "warning": "承诺高额短期回报的很可能是庞氏骗局",
                "risk_level": "极高"
            },
            {
                "type": "虚假",
                "keywords": ["官方认证", "银行托管", "保险公司担保", "政府背景", "国企背景"],
                "warning": "虚假背书，需要核实官方信息",
                "risk_level": "高"
            }
        ]
    
    def get_books(self, level=None, focus=None, recommended_only=False):
        """获取书籍列表"""
        result = self.books
        if level:
            result = [b for b in result if b['level'] == level]
        if focus:
            result = [b for b in result if focus in b['focus']]
        if recommended_only:
            result = [b for b in result if b['recommended']]
        return result
    
    def get_quotes(self, author=None, context=None):
        """获取投资金句"""
        result = self.quotes
        if author:
            result = [q for q in result if author.lower() in q['author'].lower()]
        if context:
            result = [q for q in result if context in q['context']]
        return result
    
    def check_risk(self, text):
        """检查文本中的风险关键词"""
        text_lower = text.lower()
        found_risks = []
        
        for warning in self.warnings:
            for keyword in warning['keywords']:
                if keyword in text_lower:
                    found_risks.append({
                        'type': warning['type'],
                        'keyword': keyword,
                        'warning': warning['warning'],
                        'risk_level': warning['risk_level']
                    })
                    break
        
        return found_risks
    
    def get_random_quote(self):
        """获取随机金句"""
        import random
        if self.quotes:
            return random.choice(self.quotes)
        return None
    
    def get_reading_list(self, level="入门"):
        """获取推荐阅读清单"""
        books = self.get_books(level=level, recommended_only=True)
        return books
    
    def add_quote(self, author, quote, context="投资智慧", source="用户添加"):
        """添加新金句"""
        new_quote = {
            "author": author,
            "quote": quote,
            "context": context,
            "source": source
        }
        self.quotes.append(new_quote)
        self.save()
        return new_quote
    
    def get_stats(self):
        """获取知识库统计"""
        return {
            "books_count": len(self.books),
            "quotes_count": len(self.quotes),
            "warnings_count": len(self.warnings),
            "recommended_books": len([b for b in self.books if b['recommended']])
        }
    
    def add_note(self, book, quote, reflection=""):
        """添加笔记"""
        note = {
            "book": book,
            "quote": quote,
            "reflection": reflection,
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.notes.append(note)
        self.save()
        return note
    
    def get_notes(self, book=None, keyword=None):
        """获取笔记"""
        result = self.notes
        if book:
            result = [n for n in result if book.lower() in n.get('book', '').lower()]
        if keyword:
            result = [n for n in result if keyword.lower() in n.get('quote', '').lower() or keyword.lower() in n.get('reflection', '').lower()]
        return result
    
    def search_notes(self, keyword):
        """搜索笔记"""
        return self.get_notes(keyword=keyword)


def main():
    kb = KnowledgeBase()
    
    print("="*50)
    print("投研知识库")
    print("="*50)
    
    stats = kb.get_stats()
    print(f"\n书籍数量: {stats['books_count']}")
    print(f"金句数量: {stats['quotes_count']}")
    print(f"风险规则: {stats['warnings_count']}")
    
    print("\n推荐书籍:")
    for book in kb.get_books(recommended_only=True):
        print(f"  - {book['title']} ({book['author']})")
    
    print("\n随机金句:")
    quote = kb.get_random_quote()
    if quote:
        print(f"  {quote['quote']}")
        print(f"  ——{quote['author']}")
    
    print("\n风险检测示例:")
    test_texts = [
        "保本保息，年化收益30%",
        "定期定额投资，长期持有",
        "老师带单，保证涨停",
        "分散投资，控制风险"
    ]
    for text in test_texts:
        risks = kb.check_risk(text)
        if risks:
            print(f"  [{text}] -> 发现风险: {risks[0]['type']}")
        else:
            print(f"  [{text}] -> 安全")


if __name__ == "__main__":
    main()
