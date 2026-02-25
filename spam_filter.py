import joblib
import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

class SpamFilter:
    def __init__(self, model_path=None, vectorizer_path=None):
        _here = os.path.dirname(os.path.abspath(__file__))
        if model_path is None:
            model_path = os.path.join(_here, 'spam_model.pkl')
        if vectorizer_path is None:
            vectorizer_path = os.path.join(_here, 'vectorizer.pkl')
        self.model = joblib.load(model_path)
        self.vectorizer = joblib.load(vectorizer_path)

    def get_accuracy(self, data_dir='.'):
        """Returns model accuracy (%) on the held-out test split."""
        try:
            df1 = pd.read_csv(os.path.join(data_dir, 'spam_ham_dataset.csv'))
            df2 = pd.read_csv(os.path.join(data_dir, 'emails.csv'))
            df2.rename(columns={'spam': 'label_num'}, inplace=True)
            df = pd.concat([df1[['text', 'label_num']], df2[['text', 'label_num']]], ignore_index=True)
            _, X_test, _, y_test = train_test_split(df['text'], df['label_num'], test_size=0.2, random_state=42)
            X_test_vec = self.vectorizer.transform(X_test)
            y_pred = self.model.predict(X_test_vec)
            return round(accuracy_score(y_test, y_pred) * 100, 2)
        except Exception:
            return None

    def predict(self, text):
        """
        Predicts if the text is spam or ham.
        Returns: 1 for spam, 0 for ham
        """
        text_vec = self.vectorizer.transform([text])
        prediction = self.model.predict(text_vec)
        return prediction[0]

    def is_spam(self, text):
        return self.predict(text) == 1

if __name__ == "__main__":
    # Simple test
    filter = SpamFilter()
    test_ham = "Subject: Meeting next week. Hi, are we still meeting next week to discuss the project?"
    test_spam = "Subject: Congratulations! You've won a $1000 gift card. Click here to claim your prize."
    
    print(f"Ham test: {'Spam' if filter.is_spam(test_ham) else 'Ham'}")
    print(f"Spam test: {'Spam' if filter.is_spam(test_spam) else 'Ham'}")
