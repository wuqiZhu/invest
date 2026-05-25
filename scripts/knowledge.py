# -*- coding: utf-8 -*-
"""
投研知识库独立脚本

使用方法：
    python knowledge.py --books              # 查看书籍推荐
    python knowledge.py --books --level 入门  # 按级别筛选
    python knowledge.py --quotes             # 查看投资金句
    python knowledge.py --quotes --author Buffett  # 按作者筛选
    python knowledge.py --check-risk --text "保本保息"  # 风险检测
    python knowledge.py --note --book "聪明的投资者" --text "市场短期是投票机"  # 添加笔记
    python knowledge.py --note --list        # 查看笔记

免责声明：
本工具仅供个人学习和研究使用，不构成任何投资建议。
"""

import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from knowledge_base import KnowledgeBase


def show_books(kb, level=None, focus=None, recommended=False):
    """显示推荐书籍"""
    books = kb.get_books(level=level, focus=focus, recommended_only=recommended)
    
    print("\n" + "="*50)
    print("投资书籍推荐")
    print("="*50)
    
    if not books:
        print("\n暂无符合条件的书籍")
        return
    
    for book in books:
        star = "[*]" if book['recommended'] else "[ ]"
        print(f"\n{star} {book['title']}")
        print(f"  作者: {book['author']} ({book['year']})")
        print(f"  级别: {book['level']} | 主题: {book['focus']}")
        print(f"  核心要点: {', '.join(book['key_points'])}")
    
    print(f"\n共 {len(books)} 本书")


def show_quotes(kb, author=None, context=None):
    """显示投资金句"""
    quotes = kb.get_quotes(author=author, context=context)
    
    print("\n" + "="*50)
    print("投资智慧金句")
    print("="*50)
    
    if not quotes:
        print("\n暂无符合条件的金句")
        return
    
    for quote in quotes:
        print(f"\n  {quote['quote']}")
        print(f"  --{quote['author']} ({quote['source']})")
    
    print(f"\n共 {len(quotes)} 条金句")


def check_risk(kb, text):
    """检查文本中的风险关键词"""
    risks = kb.check_risk(text)
    
    print("\n" + "="*50)
    print("风险检测结果")
    print("="*50)
    
    if not risks:
        print(f"\n[OK] 未发现风险关键词")
        print(f"检测文本: {text[:50]}...")
    else:
        print(f"\n[!] 发现 {len(risks)} 个风险关键词:")
        for risk in risks:
            print(f"\n  类型: {risk['type']}")
            print(f"  关键词: {risk['keyword']}")
            print(f"  风险等级: {risk['risk_level']}")
            print(f"  警告: {risk['warning']}")
    
    print(f"\n{'='*50}")


def add_note(kb, book, text, reflection=""):
    """添加笔记"""
    note = kb.add_note(book, text, reflection)
    print(f"\n笔记已添加:")
    print(f"  书籍: {note['book']}")
    print(f"  摘录: {note['quote']}")
    if note['reflection']:
        print(f"  反思: {note['reflection']}")
    print(f"  时间: {note['date']}")


def list_notes(kb, book=None, keyword=None):
    """列出笔记"""
    notes = kb.get_notes(book=book, keyword=keyword)
    
    print(f"\n{'='*50}")
    print("投资笔记")
    print(f"{'='*50}")
    
    if not notes:
        print("\n暂无笔记")
        return
    
    for note in notes:
        print(f"\n{note['date']}")
        print(f"  书籍: {note['book']}")
        print(f"  摘录: {note['quote']}")
        if note.get('reflection'):
            print(f"  反思: {note['reflection']}")
    
    print(f"\n{'='*50}")
    print(f"共 {len(notes)} 条笔记")


def main():
    parser = argparse.ArgumentParser(
        description='投研知识库独立脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看书籍推荐
  python knowledge.py --books
  python knowledge.py --books --level 入门
  python knowledge.py --books --recommended

  # 查看投资金句
  python knowledge.py --quotes
  python knowledge.py --quotes --author Buffett

  # 风险检测
  python knowledge.py --check-risk --text "保本保息，年化收益30%"

  # 添加笔记
  python knowledge.py --note --book "聪明的投资者" --text "市场短期是投票机" --reflection "这句话提醒我不要被短期波动影响"

  # 查看笔记
  python knowledge.py --note --list
  python knowledge.py --note --list --book "聪明的投资者"
        """
    )
    
    parser.add_argument('--books', action='store_true', help='查看书籍推荐')
    parser.add_argument('--quotes', action='store_true', help='查看投资金句')
    parser.add_argument('--check-risk', action='store_true', help='风险检测')
    parser.add_argument('--note', action='store_true', help='笔记管理')
    
    parser.add_argument('--level', choices=['入门', '进阶', '经典', '高级', '心理学'],
                       help='书籍级别（用于--books）')
    parser.add_argument('--focus', help='书籍主题（用于--books）')
    parser.add_argument('--recommended', action='store_true', help='仅显示推荐书籍')
    parser.add_argument('--author', help='作者名称（用于--quotes）')
    parser.add_argument('--context', help='金句上下文（用于--quotes）')
    parser.add_argument('--text', help='待检测文本（用于--check-risk）或笔记摘录（用于--note）')
    parser.add_argument('--book', help='书籍名称（用于--note）')
    parser.add_argument('--reflection', default='', help='反思内容（用于--note）')
    parser.add_argument('--list', action='store_true', help='列出笔记（用于--note）')
    
    parser.add_argument('--db', help='知识库数据库路径')
    
    args = parser.parse_args()
    
    kb = KnowledgeBase(args.db)
    
    if args.books:
        show_books(kb, level=args.level, focus=args.focus, recommended=args.recommended)
    elif args.quotes:
        show_quotes(kb, author=args.author, context=args.context)
    elif args.check_risk:
        if not args.text:
            print("风险检测需要指定文本: --text '待检测文本'")
            return
        check_risk(kb, args.text)
    elif args.note:
        if args.list:
            list_notes(kb, book=args.book)
        elif args.book and args.text:
            add_note(kb, args.book, args.text, args.reflection)
        else:
            print("笔记操作需要指定: --list 或 --book '书名' --text '摘录'")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
