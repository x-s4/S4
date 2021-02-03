import pandas as pd
from scipy import stats
from scipy.stats import chi2_contingency
from statsmodels.stats.multitest import fdrcorrection
from statsmodels.stats.weightstats import ztest

from src.core.config import THRESHOLD_NORMAL_DIST
from src.utils.tools import format_split_name


# noinspection PyMethodMayBeStatic
class StatisticalTestErrorControl:

    def compute_adjusted_pvalue(self, df, error_control, threshold):
        if error_control == "FDR":
            self.adjusted_pvalue_FDR(df, threshold)
            return
        raise Exception("Control type not defined ")

    def adjusted_pvalue_FDR(self, df, threshold=0.05):
        a, b = fdrcorrection(df["p-value"], is_sorted=True, alpha=threshold)
        df["p-value (FDR)"] = b
        df = df[a]


def aggregate_values(df, freq="D", col="purchase"):
    return df.groupby(pd.Grouper(freq=freq)).agg({"purchase": "sum"})[col].values


class StatisticalTestHandler:

    def evaluate(self, test_type, cases, test_arg, distribution_check=False):
        if distribution_check:
            pass
        if test_type == "mean":
            return self.mean_evaluation(cases, test_arg)
        raise Exception("test type not implemented yet ")

    def mean_evaluation(self, cases, test_arg):
        res = []
        if test_arg == "One-Sample":
            test_func = self.one_sample_mean_test
        elif test_arg == "Two-Samples":
            test_func = self.two_sample_mean_test
        elif test_arg[0] == "z_test":
            test_func = self.z_test
        else:
            raise NotImplementedError("Mean test type not implemented")
        self.test_arg = test_arg
        for idx, (i, j) in enumerate(cases):
            if i.shape[0] == 0 or j.shape[0] == 0:
                continue
            res.append(
                (*format_split_name(i), len(i), *format_split_name(j), len(j), *test_func(i, j)))

        result = pd.DataFrame(res)
        result.columns = [
            "e", "e_µ", "e_std", "e_size", "h", "h_µ", "h_std", "h_size", "t-value", "p-value", "e_normal", "h_normal",
            "chi-squared test"
        ]
        return result.sort_values("p-value")

    def one_sample_mean_test(self, i, j):
        values_1 = aggregate_values(i)
        t_normal = self.test_normal_distribution(values_1)
        return *stats.ttest_1samp(values_1, j[0]), t_normal, True, 1

    def two_sample_mean_test(self, i, j):
        values_1 = aggregate_values(i)
        values_2 = aggregate_values(j)
        t_normal = self.test_normal_distribution(values_1)
        r_normal = self.test_normal_distribution(values_2)

        if not (t_normal and r_normal):
            values_1 = (values_1 - min(values_1)) / (max(values_1) - min(values_1))
            values_2 = (values_2 - min(values_2)) / (max(values_2) - min(values_2))

        contingency_df = self.generate_contingency_table(values_1, values_2)
        stat, p, dof, expected = chi2_contingency(contingency_df)
        return *stats.ttest_ind(values_1, values_2, equal_var=True), t_normal, r_normal, p

    def z_test(self, i, j, freq="D"):
        values_1 = aggregate_values(df=i, freq=freq) / self.test_arg[1]
        values_2 = aggregate_values(df=j, freq=freq) / self.test_arg[1]
        t_normal = self.test_normal_distribution(values_1)
        r_normal = self.test_normal_distribution(values_2)

        if not (t_normal and r_normal):
            values_1 = (values_1 - min(values_1)) / (max(values_1) - min(values_1))
            values_2 = (values_2 - min(values_2)) / (max(values_2) - min(values_2))

        contingency_df = self.generate_contingency_table(values_1, values_2)
        stat, p, dof, expected = chi2_contingency(contingency_df)
        print(ztest(values_1, values_2)[1])
        return *ztest(values_1, values_2), t_normal, r_normal, p

    def test_normal_distribution(self, values_1, threshold_normal_dist=THRESHOLD_NORMAL_DIST):
        return len(values_1) >= 8 and stats.normaltest(values_1)[1] >= threshold_normal_dist

    def generate_contingency_table(self, values_1, values_2):
        data = pd.DataFrame([values_1, values_2]).T.fillna(0).astype(bool)
        return pd.DataFrame([data[0].value_counts(), data[1].value_counts()]).T
