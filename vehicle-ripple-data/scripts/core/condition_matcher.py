#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
条件ID匹配器 - 多级模糊匹配策略

提供智能的条件ID匹配功能，支持：
1. 精确匹配
2. 规范化匹配（去除括号等变体）
3. 编辑距离模糊匹配
4. 特征提取匹配（处理GBK编码乱码）

适用于vehicle-ripple-data和vehicle-slope-data技能
"""

import re
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class MatchResult:
    """匹配结果"""
    condition_name: str
    matched_id: str
    match_type: str  # 'exact', 'normalized', 'fuzzy', 'feature'
    confidence: float  # 0.0-1.0


class ConditionMatcher:
    """
    条件ID智能匹配器
    
    使用多级匹配策略，提高条件名称查找的容错性
    """
    
    def __init__(self, test_rules: Dict[str, Dict]):
        """
        初始化匹配器
        
        Args:
            test_rules: 测试命名规则字典 {condition_id: {condition_name: ..., soc_level: ...}}
        """
        self.test_rules = test_rules

        # 预计算规范化版本用于快速查找
        self._normalized_map = self._build_normalized_map()

        # 预编译坡度前缀正则,避免 _extract_features 频繁调用时重复编译
        # (?![0-9]) 负向前瞻: 确保 "10" 后面不是数字,避免误匹配 "坡度100"
        self._slope_prefix_pattern = re.compile(
            r'^(坡度|�¶�)\s*10(?![0-9])[_\-\s]*',
            re.IGNORECASE
        )

        # 特征模式定义（用于处理GBK乱码）
        self._keyword_patterns = {
            '超车': ['超车', '�'],
            '急减速': ['急减速', '����'],
            '急刹车': ['急刹车', '��ɲ��'],
            '急加速': ['急加速', '������'],
            '滑行': ['滑行', '����'],
            '停车': ['停车', 'ͣ��'],
            '匀速': ['匀速', '����'],
            '暖风': ['暖风', 'ů��', '热风', '����'],
            '冷风': ['冷风', '���', '���'],
            '直流充电': ['直流充电', 'ֱ�����'],
            '交流充电': ['交流充电', '������'],
            'D档': ['D档', 'D��'],
            '多次加速': ['多次加速'],
            '爬坡': ['爬坡', '坡度', '�¶�'],
        }
    
    def _build_normalized_map(self) -> Dict[str, str]:
        """
        构建规范化ID到原始ID的映射
        
        去除括号、空格等变体字符
        """
        normalized_map = {}
        for condition_id in self.test_rules.keys():
            normalized = self._normalize_id(condition_id)
            normalized_map[normalized] = condition_id
        return normalized_map
    
    def _normalize_id(self, condition_id: str) -> str:
        """
        规范化条件ID
        
        去除：
        - 中英文括号 ()（）
        - 空格
        - 特殊模式标记
        """
        # 去除括号和空格
        normalized = re.sub(r'[()（）\s]', '', condition_id)
        # 统一大小写（如果有英文）
        normalized = normalized.lower()
        return normalized
    
    def match(self, condition_id: str, min_confidence: float = 0.7) -> Optional[MatchResult]:
        """
        多级匹配入口
        
        按优先级依次尝试：
        1. 精确匹配
        2. 规范化匹配
        3. 编辑距离模糊匹配
        4. 特征匹配（处理编码问题）
        
        Args:
            condition_id: 要匹配的条件ID
            min_confidence: 最小置信度阈值（0.0-1.0）
            
        Returns:
            MatchResult对象或None
        """
        # 级别1: 精确匹配
        result = self._exact_match(condition_id)
        if result:
            return result
        
        # 级别2: 规范化匹配
        result = self._normalized_match(condition_id)
        if result:
            return result

        # 级别2.5: SOC 容差匹配 (描述相同,仅 SOC 偏差 ≤5)
        result = self._soc_tolerant_match(condition_id, soc_tolerance=5)
        if result:
            return result

        # 级别3: 编辑距离模糊匹配
        result = self._fuzzy_match(condition_id, threshold=min_confidence)
        if result:
            return result
        
        # 级别4: 特征匹配（处理GBK乱码）
        result = self._feature_match(condition_id, min_score=5)
        if result:
            return result
        
        return None
    
    def _exact_match(self, condition_id: str) -> Optional[MatchResult]:
        """精确匹配"""
        if condition_id in self.test_rules:
            rule_info = self.test_rules[condition_id]
            return MatchResult(
                condition_name=rule_info.get('condition_name', condition_id),
                matched_id=condition_id,
                match_type='exact',
                confidence=1.0
            )
        return None
    
    def _normalized_match(self, condition_id: str) -> Optional[MatchResult]:
        """规范化匹配（去除括号差异）"""
        normalized_id = self._normalize_id(condition_id)

        if normalized_id in self._normalized_map:
            matched_id = self._normalized_map[normalized_id]
            rule_info = self.test_rules[matched_id]
            return MatchResult(
                condition_name=rule_info.get('condition_name', condition_id),
                matched_id=matched_id,
                match_type='normalized',
                confidence=0.95
            )
        return None

    def _get_description_part(self, condition_id: str) -> str:
        """提取 condition_id 的描述部分（去掉 SOC 值和运动模式后缀）

        例如: '坡度10_82_匀速80暖风' -> '匀速80暖风'
              '87_超车80-140(运动模式)' -> '超车80-140'
        """
        working_id = condition_id
        # 去掉坡度前缀
        if self._slope_prefix_pattern.search(working_id):
            working_id = self._slope_prefix_pattern.sub('', working_id)
        # 去掉开头的 SOC 值
        soc_match = re.match(r'^(\d+)[_\-\s](.*)', working_id)
        if soc_match:
            working_id = soc_match.group(2)
        # 去掉运动模式后缀（中英文括号）
        working_id = re.sub(r'[(（]运动模式[)）]', '', working_id)
        return working_id

    def _soc_tolerant_match(self, condition_id: str, soc_tolerance: int = 5) -> Optional[MatchResult]:
        """SOC 容差匹配: 描述部分相同,仅 SOC 值在容差范围内时视为高置信度匹配"""
        if not self.test_rules:
            return None

        input_features = self._extract_features(condition_id)
        if input_features['soc'] is None:
            return None

        input_desc = self._get_description_part(condition_id)
        if not input_desc:
            return None

        best_match = None
        best_soc_diff = float('inf')

        for rule_id, rule_info in self.test_rules.items():
            rule_features = self._extract_features(rule_id)

            # 坡度标识必须一致
            if input_features['is_slope'] != rule_features['is_slope']:
                continue

            # 规则必须有 SOC
            if rule_features['soc'] is None:
                continue

            # 描述部分必须一致
            rule_desc = self._get_description_part(rule_id)
            if input_desc != rule_desc:
                continue

            # SOC 值在容差范围内
            soc_diff = abs(input_features['soc'] - rule_features['soc'])
            if soc_diff <= soc_tolerance and soc_diff < best_soc_diff:
                best_soc_diff = soc_diff
                best_match = rule_id

        if best_match:
            rule_info = self.test_rules[best_match]
            # 差值越小置信度越高: 0 差值=0.95, 5 差值=0.90
            confidence = 0.95 - (best_soc_diff * 0.01)
            return MatchResult(
                condition_name=rule_info.get('condition_name', condition_id),
                matched_id=best_match,
                match_type='soc_tolerant',
                confidence=round(confidence, 2)
            )

        return None

    def _fuzzy_match(self, condition_id: str, threshold: float = 0.7) -> Optional[MatchResult]:
        """
        基于编辑距离的模糊匹配

        使用Levenshtein距离计算相似度
        增加关键词冲突检查，避免明显的语义错误匹配
        """
        if not self.test_rules:
            return None

        best_match = None
        best_score = 0.0

        normalized_input = self._normalize_id(condition_id)
        input_features = self._extract_features(condition_id)

        for rule_id in self.test_rules.keys():
            normalized_rule = self._normalize_id(rule_id)

            # 计算相似度
            similarity = self._calculate_similarity(normalized_input, normalized_rule)

            # 关键词冲突检查：如果存在互斥关键词，降低相似度
            rule_features = self._extract_features(rule_id)
            conflict_penalty = self._calculate_keyword_conflict(input_features, rule_features)
            adjusted_similarity = similarity * (1 - conflict_penalty)

            # 坡度/非坡度类别隔离: 如果一个是坡度另一个不是,直接阻断
            if input_features['is_slope'] != rule_features['is_slope']:
                adjusted_similarity = 0.0

            if adjusted_similarity > best_score:
                best_score = adjusted_similarity
                best_match = rule_id

        if best_match and best_score >= threshold:
            rule_info = self.test_rules[best_match]
            return MatchResult(
                condition_name=rule_info.get('condition_name', condition_id),
                matched_id=best_match,
                match_type='fuzzy',
                confidence=best_score
            )

        return None

    def _calculate_keyword_conflict(self, features1: Dict, features2: Dict) -> float:
        """
        计算关键词冲突惩罚

        如果两个条件ID包含互斥的关键词（如暖风 vs 冷风），
        返回一个惩罚值来降低匹配分数

        Returns:
            惩罚值 0.0-0.5（0表示无冲突，0.5表示严重冲突）
        """
        # 定义互斥关键词组
        exclusive_groups = [
            {'暖风', '冷风', '热风'},
            {'充电', '放电'},
            {'加速', '减速', '刹车'},
            {'直流充电', '交流充电'},  # 充电方式不同
        ]

        keywords1 = set(features1.get('keywords', []))
        keywords2 = set(features2.get('keywords', []))

        penalty = 0.0

        for group in exclusive_groups:
            # 检查是否来自同一互斥组但不同关键词
            overlap1 = keywords1 & group
            overlap2 = keywords2 & group

            if overlap1 and overlap2 and overlap1 != overlap2:
                # 发现互斥冲突，增加惩罚
                penalty += 0.3

        return min(penalty, 0.5)  # 最高惩罚0.5
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """
        计算两个字符串的相似度（基于Levenshtein距离）
        
        Returns:
            相似度分数 0.0-1.0
        """
        distance = self._levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        
        if max_len == 0:
            return 1.0
        
        return 1.0 - (distance / max_len)
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        计算Levenshtein编辑距离
        
        动态规划实现
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # 计算插入、删除、替换的成本
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _feature_match(self, condition_id: str, min_score: int = 5) -> Optional[MatchResult]:
        """
        基于特征提取的匹配（专门处理GBK编码乱码）

        提取条件ID的特征（坡度标识、SOC值、关键词）进行匹配
        增加关键词冲突检查，避免明显的语义错误匹配
        """
        input_features = self._extract_features(condition_id)

        if not input_features['keywords']:
            return None

        best_match = None
        best_score = 0
        best_matched_name = None

        for rule_id, rule_info in self.test_rules.items():
            score = 0
            rule_features = self._extract_features(rule_id)

            # 检查关键词冲突（严重冲突直接跳过）
            conflict_penalty = self._calculate_keyword_conflict(input_features, rule_features)
            if conflict_penalty >= 0.3:  # 互斥关键词，严重冲突
                continue  # 跳过此规则

            # 1. 检查坡度工况是否匹配 (+10分)
            if input_features['is_slope'] == rule_features['is_slope']:
                score += 10

            # 坡度类别严重不匹配时,大幅惩罚
            if input_features['is_slope'] != rule_features['is_slope']:
                # 若输入明确为坡度但规则不是,或反之,视为严重不匹配
                if input_features['is_slope'] or rule_features['is_slope']:
                    # 至少一方明确标记为坡度,但另一方不是 → 大概率是不同类别
                    score -= 15  # 大幅惩罚,使非同类规则难以竞争

            # 2. 检查关键词匹配 (+5分/个)
            for keyword in input_features['keywords']:
                if keyword in rule_features['keywords']:
                    score += 5

            # 3. 如果SOC可用，检查SOC范围一致性 (+3分)
            if input_features['soc'] is not None and rule_features['soc'] is not None:
                soc_level = rule_info.get('soc_level', '')
                soc_value = input_features['soc']

                if '≥70%' in soc_level and soc_value >= 70:
                    score += 3
                elif '40%-70%' in soc_level and 40 <= soc_value < 70:
                    score += 3
                elif '≤40%' in soc_level and soc_value < 40:
                    score += 3

            if score > best_score:
                best_score = score
                best_match = rule_id
                best_matched_name = rule_info.get('condition_name', condition_id)

        # 至少需要一个关键词匹配才返回
        if best_score >= min_score:
            confidence = min(0.9, best_score / 20.0)  # 最高0.9置信度
            return MatchResult(
                condition_name=best_matched_name,
                matched_id=best_match,
                match_type='feature',
                confidence=confidence
            )

        return None
    
    def _extract_features(self, condition_id: str) -> Dict:
        """
        从condition_id提取特征
        
        特征包括：
        - is_slope: 是否为坡度工况
        - soc: SOC值
        - keywords: 关键词列表
        """
        features = {
            'is_slope': False,
            'soc': None,
            'keywords': []
        }
        
        working_id = condition_id

        # 检查是否为坡度工况（支持正常文本和GBK乱码）
        # 支持: 坡度10_xxx, 坡度10 xxx, 坡度10-xxx, 坡度10xxx,
        #        坡度10__xxx(双下划线) 等任意分隔符变体
        if self._slope_prefix_pattern.search(condition_id):
            features['is_slope'] = True
            # 去掉前缀后的 working_id
            working_id = self._slope_prefix_pattern.sub('', condition_id)
        
        # 提取SOC值（第一个数字 + 任意分隔符）
        soc_match = re.match(r'^(\d+)[_\-\s](.*)', working_id)
        if soc_match:
            features['soc'] = int(soc_match.group(1))
            working_id = soc_match.group(2)
        
        # 提取关键词
        for keyword, patterns in self._keyword_patterns.items():
            for pattern in patterns:
                if pattern in working_id or pattern in condition_id:
                    features['keywords'].append(keyword)
                    break
        
        return features
    
    def get_match_details(self, condition_id: str) -> Dict:
        """
        获取详细的匹配信息（用于调试）
        
        返回每个匹配级别的结果
        """
        details = {
            'input': condition_id,
            'exact_match': None,
            'normalized_match': None,
            'soc_tolerant_match': None,
            'fuzzy_matches': [],
            'feature_match': None,
            'final_result': None
        }

        # 精确匹配
        exact = self._exact_match(condition_id)
        if exact:
            details['exact_match'] = {
                'matched_id': exact.matched_id,
                'condition_name': exact.condition_name,
                'confidence': exact.confidence
            }
            details['final_result'] = details['exact_match']
            return details

        # 规范化匹配
        normalized = self._normalized_match(condition_id)
        if normalized:
            details['normalized_match'] = {
                'matched_id': normalized.matched_id,
                'condition_name': normalized.condition_name,
                'confidence': normalized.confidence
            }
            details['final_result'] = details['normalized_match']
            return details

        # SOC 容差匹配
        soc_tolerant = self._soc_tolerant_match(condition_id)
        if soc_tolerant:
            details['soc_tolerant_match'] = {
                'matched_id': soc_tolerant.matched_id,
                'condition_name': soc_tolerant.condition_name,
                'confidence': soc_tolerant.confidence
            }
            details['final_result'] = details['soc_tolerant_match']
            return details

        # 模糊匹配（返回前3个）
        input_features = self._extract_features(condition_id)
        normalized_input = self._normalize_id(condition_id)
        matches = []
        for rule_id in self.test_rules.keys():
            normalized_rule = self._normalize_id(rule_id)
            similarity = self._calculate_similarity(normalized_input, normalized_rule)

            # 坡度类别隔离: 跳过跨类别匹配
            rule_features = self._extract_features(rule_id)
            if input_features['is_slope'] != rule_features['is_slope']:
                continue

            if similarity >= 0.5:
                matches.append((rule_id, similarity))

        matches.sort(key=lambda x: x[1], reverse=True)
        for rule_id, similarity in matches[:3]:
            rule_info = self.test_rules[rule_id]
            details['fuzzy_matches'].append({
                'matched_id': rule_id,
                'condition_name': rule_info.get('condition_name', ''),
                'confidence': similarity
            })
        
        if matches and matches[0][1] >= 0.7:
            best_id, best_score = matches[0]
            rule_info = self.test_rules[best_id]
            details['final_result'] = {
                'matched_id': best_id,
                'condition_name': rule_info.get('condition_name', ''),
                'confidence': best_score,
                'match_type': 'fuzzy'
            }
            return details
        
        # 特征匹配
        feature = self._feature_match(condition_id, min_score=3)
        if feature:
            details['feature_match'] = {
                'matched_id': feature.matched_id,
                'condition_name': feature.condition_name,
                'confidence': feature.confidence
            }
            details['final_result'] = details['feature_match']
            return details
        
        return details


# 便捷函数，向后兼容
def get_condition_name(condition_id: str, test_rules: Dict[str, Dict]) -> str:
    """
    获取条件名称（简化接口，向后兼容）
    
    这是原有_get_condition_name方法的替代实现
    
    Args:
        condition_id: 条件ID
        test_rules: 测试命名规则字典
        
    Returns:
        条件名称（如果匹配失败则返回ID的描述部分）
    """
    matcher = ConditionMatcher(test_rules)
    result = matcher.match(condition_id)
    
    if result:
        return result.condition_name
    
    # 回退：从condition_id提取描述部分
    parts = condition_id.split('_', 1)
    if len(parts) > 1:
        return parts[1]
    return condition_id


# 测试代码
if __name__ == '__main__':
    # 示例测试规则
    test_rules = {
        '87_超车80-140(运动模式)': {'condition_name': '超越加速', 'soc_level': '≥70%'},
        '87_超车80-140（运动模式）': {'condition_name': '超越加速', 'soc_level': '≥70%'},
        '26_超车80-140（运动模式）': {'condition_name': '超越加速', 'soc_level': '≤40%'},
        '坡度10_81_匀速80暖风（运动模式）': {'condition_name': '爬坡高温', 'soc_level': '≥70%'},
        '坡度10_75_匀速80冷风（运动模式）': {'condition_name': '爬坡低温', 'soc_level': '≥70%'},
        '20_直流充电暖风': {'condition_name': '直流充电暖风', 'soc_level': '≤40%'},
        '90_停车D档热风': {'condition_name': '静止高温', 'soc_level': '≥70%'},
    }
    
    matcher = ConditionMatcher(test_rules)
    
    # 测试各种情况
    test_cases = [
        '87_超车80-140(运动模式)',      # 精确匹配
        '87_超车80-140（运动模式）',     # 括号变体
        '87_超车80-140(运动模式',       # 括号不匹配
        '坡度10_81_匀速80暖风（运动模式）', # 坡度工况
        '�¶�10_81_匀速80暖风（运动模式）', # GBK乱码
        '88_超车80-140(运动模式)',      # 不存在的ID（SOC不同）
        '87_超车80-140运动模式',        # 缺少括号

        # 坡度前缀分隔符变体(下划线/空格/连字符) + 匀速暖风工况
        '坡度10_93_匀速80暖风',           # 标准格式 → 应匹配爬坡高温
        '坡度10 93_匀速80暖风',            # 前缀空格 + 描述下划线
        '坡度10 93 匀速80暖风',            # 前缀空格 + 描述空格
        '坡度10 93-匀速80暖风',            # 前缀空格 + 描述连字符
        '坡度10-93_匀速80暖风',            # 前缀连字符 + 描述下划线

        # 坡度前缀分隔符变体 + 匀速冷风工况
        '坡度10_93_匀速80冷风',           # 标准格式 → 应匹配爬坡低温
        '坡度10 93 匀速80冷风',            # 前缀空格 + 描述空格
        '坡度10 93-匀速80冷风',            # 前缀空格 + 描述连字符
        '坡度10-93_匀速80冷风',            # 前缀连字符 + 描述下划线

        # 坡度前缀 + 简化描述(无"80"数字)
        '坡度10_93_匀速暖风',             # 简化描述 → 应匹配爬坡高温
        '坡度10_93_匀速冷风',             # 简化描述 → 应匹配爬坡低温

        # 坡度前缀 + 急加速工况(各种分隔符和描述变体)
        '坡度10 93_急加速',               # 空格+下划线,无SOC后数字 → 应匹配爬坡
        '坡度10 93 急加速',                # 全空格分隔
        '坡度10 93-急加速',                # 前缀空格 + 描述连字符
        '坡度10 93_加速',                  # 缺少"急"字 → 仍应匹配爬坡(坡度关键词保底)
        '坡度10 93_加速0-80',              # 描述含连字符范围 → 仍应匹配爬坡
    ]
    
    print("条件ID模糊匹配测试")
    print("=" * 80)
    
    for test_id in test_cases:
        print(f"\n输入: {test_id}")
        result = matcher.match(test_id)
        
        if result:
            print(f"  [OK] 匹配成功")
            print(f"    匹配ID: {result.matched_id}")
            print(f"    条件名: {result.condition_name}")
            print(f"    匹配类型: {result.match_type}")
            print(f"    置信度: {result.confidence:.2f}")
        else:
            print(f"  [FAIL] 匹配失败")
            # 显示详细匹配信息
            details = matcher.get_match_details(test_id)
            if details['fuzzy_matches']:
                print(f"    相似候选:")
                for match in details['fuzzy_matches'][:2]:
                    print(f"      - {match['matched_id']}: {match['confidence']:.2f}")
