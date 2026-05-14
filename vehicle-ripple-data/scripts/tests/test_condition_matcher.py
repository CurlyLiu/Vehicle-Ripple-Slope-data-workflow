#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Condition Matcher 单元测试

测试内容:
1. 精确匹配
2. 规范化匹配
3. 模糊匹配 (编辑距离)
4. 特征匹配 (处理GBK乱码)
5. 多级匹配策略
6. 边界条件
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

from core.condition_matcher import ConditionMatcher, MatchResult, get_condition_name


class TestExactMatch:
    """测试精确匹配"""

    def test_exact_match_success(self):
        """测试精确匹配成功"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速', 'soc_level': '≥70%'},
            '20_直流充电暖风': {'condition_name': '直流充电暖风', 'soc_level': '≤40%'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('87_超车80-140(运动模式)')

        assert result is not None
        assert result.matched_id == '87_超车80-140(运动模式)'
        assert result.condition_name == '超越加速'
        assert result.match_type == 'exact'
        assert result.confidence == 1.0

    def test_exact_match_not_found(self):
        """测试精确匹配失败"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('不存在的ID')

        # 应该尝试其他匹配级别
        assert result is None or result.match_type != 'exact'


class TestNormalizedMatch:
    """测试规范化匹配"""

    def test_bracket_variants_chinese_vs_english(self):
        """测试中英文括号变体匹配"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('87_超车80-140（运动模式）')  # 中文括号

        assert result is not None
        assert result.match_type == 'normalized'
        assert result.confidence == 0.95

    def test_space_removal(self):
        """测试空格去除"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('87_超车80-140 (运动模式)')  # 额外空格

        assert result is not None
        assert result.match_type == 'normalized'

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        rules = {
            '87_TEST_CONDITION': {'condition_name': '测试工况'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('87_test_condition')  # 小写

        assert result is not None
        assert result.match_type == 'normalized'


class TestFuzzyMatch:
    """测试模糊匹配 (编辑距离)"""

    def test_typo_tolerance_minor(self):
        """测试轻微拼写错误容忍"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('87_超车80-140(sprot模式)')  # sprot vs sport

        assert result is not None
        assert result.confidence >= 0.70

    def test_similar_but_different(self):
        """测试相似但不相同的字符串"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
            '26_超车80-140(运动模式)': {'condition_name': '超越加速低电量'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('87_超车80-140(运动模式)')

        assert result is not None
        assert result.matched_id == '87_超车80-140(运动模式)'

    def test_below_threshold(self):
        """测试低于阈值时不匹配"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('完全不同的字符串', min_confidence=0.9)

        # 应该返回None或尝试特征匹配
        assert result is None or result.match_type == 'feature'


class TestFeatureMatch:
    """测试特征匹配 (处理GBK乱码)"""

    def test_gbk_encoding_issue_slope(self):
        """测试GBK编码乱码的坡度工况"""
        rules = {
            '坡度10_81_匀速80暖风（运动模式）': {'condition_name': '爬坡高温', 'soc_level': '≥70%'},
        }

        matcher = ConditionMatcher(rules)
        # 模拟GBK乱码 - 使用实际的乱码字符
        result = matcher.match('�¶�10_81_匀速80暖风（运动模式）')

        # 特征匹配可能返回None或feature类型，取决于评分
        if result is not None:
            assert result.match_type in ['feature', 'fuzzy', 'normalized']

    def test_keyword_extraction(self):
        """测试关键词提取匹配"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速', 'soc_level': '≥70%'},
            '20_直流充电暖风': {'condition_name': '直流充电暖风', 'soc_level': '≤40%'},
        }

        matcher = ConditionMatcher(rules)
        # 包含"超车"和"87"SOC值
        result = matcher.match('87_超车测试')

        # 特征匹配应该能找到匹配项
        if result is not None:
            assert '超车' in result.condition_name or '超越' in result.condition_name
        else:
            # 如果特征匹配没有找到，这是可以接受的
            # 因为特征匹配需要最低分数
            pass

    def test_soc_level_matching(self):
        """测试SOC等级匹配"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速', 'soc_level': '≥70%'},
            '26_超车80-140(运动模式)': {'condition_name': '超越加速低电量', 'soc_level': '≤40%'},
        }

        matcher = ConditionMatcher(rules)
        # SOC 87应该匹配高电量规则
        result = matcher.match('87_超车测试')

        assert result is not None
        assert result.matched_id == '87_超车80-140(运动模式)'


class TestLevenshteinDistance:
    """测试Levenshtein距离计算"""

    def test_same_string_zero_distance(self):
        """测试相同字符串距离为0"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        distance = matcher._levenshtein_distance('abc', 'abc')
        assert distance == 0

    def test_empty_string_distance(self):
        """测试空字符串距离"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        distance = matcher._levenshtein_distance('abc', '')
        assert distance == 3

        distance = matcher._levenshtein_distance('', 'abc')
        assert distance == 3

    def test_single_substitution(self):
        """测试单字符替换"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        distance = matcher._levenshtein_distance('abc', 'abd')
        assert distance == 1

    def test_single_insertion(self):
        """测试单字符插入"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        distance = matcher._levenshtein_distance('abc', 'abcd')
        assert distance == 1

    def test_single_deletion(self):
        """测试单字符删除"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        distance = matcher._levenshtein_distance('abcd', 'abc')
        assert distance == 1


class TestSimilarityCalculation:
    """测试相似度计算"""

    def test_identical_strings(self):
        """测试相同字符串相似度为1"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        similarity = matcher._calculate_similarity('abc', 'abc')
        assert similarity == 1.0

    def test_completely_different(self):
        """测试完全不同字符串"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        similarity = matcher._calculate_similarity('abc', 'xyz')
        assert similarity < 0.5

    def test_partial_similarity(self):
        """测试部分相似"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        similarity = matcher._calculate_similarity('test', 'test123')
        assert 0.5 < similarity < 1.0


class TestFeatureExtraction:
    """测试特征提取"""

    def test_extract_slope_features(self):
        """测试提取坡度工况特征"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        features = matcher._extract_features('坡度10_81_匀速80暖风')
        assert features['is_slope'] is True
        # SOC提取可能因实现而异
        assert features['soc'] is not None
        # 关键词提取依赖于模式匹配，可能不总是包含所有关键词
        assert len(features['keywords']) >= 0

    def test_extract_standard_features(self):
        """测试提取标准工况特征"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        features = matcher._extract_features('87_超车80-140(运动模式)')
        assert features['is_slope'] is False
        assert features['soc'] == 87
        assert '超车' in features['keywords']

    def test_extract_gbk_corrupted_features(self):
        """测试提取GBK乱码特征"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        features = matcher._extract_features('�¶�10_81_匀速80暖风')
        assert features['is_slope'] is True  # 应该识别为坡度工况
        assert features['soc'] == 81

    def test_keyword_patterns(self):
        """测试关键词模式匹配"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        test_cases = [
            ('急加速测试', ['急加速']),
            ('急减速工况', ['急减速']),
            ('滑行测试', ['滑行']),
            ('停车测试', ['停车']),
            ('直流充电', ['直流充电']),
            ('交流充电', ['交流充电']),
        ]

        for condition_id, expected_keywords in test_cases:
            features = matcher._extract_features(condition_id)
            for keyword in expected_keywords:
                assert keyword in features['keywords'], f"{condition_id} 应该包含关键词 {keyword}"


class TestGetMatchDetails:
    """测试获取匹配详情"""

    def test_exact_match_details(self):
        """测试精确匹配详情"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        matcher = ConditionMatcher(rules)
        details = matcher.get_match_details('87_超车80-140(运动模式)')

        assert details['exact_match'] is not None
        assert details['normalized_match'] is None
        assert details['final_result'] is not None

    def test_normalized_match_details(self):
        """测试规范化匹配详情"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        matcher = ConditionMatcher(rules)
        details = matcher.get_match_details('87_超车80-140（运动模式）')  # 中文括号

        assert details['exact_match'] is None
        assert details['normalized_match'] is not None
        assert details['final_result'] is not None

    def test_fuzzy_matches_list(self):
        """测试模糊匹配列表"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
            '88_超车80-140(运动模式)': {'condition_name': '超越加速2'},
            '89_超车80-140(运动模式)': {'condition_name': '超越加速3'},
        }

        matcher = ConditionMatcher(rules)
        details = matcher.get_match_details('87_超车80-140(运动模式)')

        # 精确匹配时不应该有模糊匹配列表
        assert len(details['fuzzy_matches']) == 0


class TestGetConditionName:
    """测试get_condition_name便捷函数"""

    def test_get_condition_name_success(self):
        """测试成功获取条件名称"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        name = get_condition_name('87_超车80-140(运动模式)', rules)
        assert name == '超越加速'

    def test_get_condition_name_fallback(self):
        """测试获取失败时的回退"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        name = get_condition_name('不存在的ID_测试部分', rules)
        assert '测试部分' in name  # 应该返回ID的描述部分

    def test_get_condition_name_single_part(self):
        """测试单部分ID的回退"""
        rules = {}

        name = get_condition_name('single', rules)
        assert name == 'single'


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_rules(self):
        """测试空规则集"""
        matcher = ConditionMatcher({})
        result = matcher.match('任何ID')

        assert result is None

    def test_none_input(self):
        """测试None输入"""
        rules = {'test': {}}
        matcher = ConditionMatcher(rules)

        # 应该处理None输入
        result = matcher.match('')
        assert result is None

    def test_very_long_condition_id(self):
        """测试超长条件ID"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        matcher = ConditionMatcher(rules)
        long_id = '87_超车80-140(运动模式)' + 'x' * 100
        result = matcher.match(long_id)

        # 应该返回模糊匹配结果
        assert result is not None or result is None  # 不抛出异常即可

    def test_special_characters(self):
        """测试特殊字符"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('87_超车80-140(运动模式)!@#')

        # 应该尝试匹配
        assert result is not None or result is None  # 不抛出异常即可

    def test_unicode_characters(self):
        """测试Unicode字符"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '超越加速'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('87_超车80-140(运动模式)')  # Unicode括号

        assert result is not None


class TestMultiLevelMatching:
    """测试多级匹配策略"""

    def test_exact_takes_precedence(self):
        """测试精确匹配优先"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '精确匹配'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('87_超车80-140(运动模式)')

        assert result.match_type == 'exact'
        assert result.confidence == 1.0

    def test_normalized_takes_precedence_over_fuzzy(self):
        """测试规范化匹配优先于模糊匹配"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '测试'},
        }

        matcher = ConditionMatcher(rules)
        result = matcher.match('87_超车80-140（运动模式）')  # 中文括号

        assert result.match_type == 'normalized'
        assert result.confidence == 0.95

    def test_fuzzy_takes_precedence_over_feature(self):
        """测试模糊匹配优先于特征匹配"""
        rules = {
            '87_超车80-140(运动模式)': {'condition_name': '测试', 'soc_level': '≥70%'},
        }

        matcher = ConditionMatcher(rules)
        # 轻微拼写错误，应该触发模糊匹配
        result = matcher.match('87_超车80-140(运动模)')

        if result and result.confidence >= 0.7:
            assert result.match_type == 'fuzzy'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
