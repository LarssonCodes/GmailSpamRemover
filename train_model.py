import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report
import joblib

def train():
    # Load dataset
    print("Loading datasets...")
    df1 = pd.read_csv('spam_ham_dataset.csv')
    df2 = pd.read_csv('emails.csv')
    
    # Preprocessing
    # df1 has 'text' and 'label_num'
    # df2 has 'text' and 'spam' -> rename 'spam' to 'label_num'
    df2.rename(columns={'spam': 'label_num'}, inplace=True)
    
    # Combined dataset
    df = pd.concat([df1[['text', 'label_num']], df2[['text', 'label_num']]], ignore_index=True)
    print(f"Total samples after merging: {len(df)}")

    X = df['text']
    y = df['label_num']
    
    # Split into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Vectorization
    print("Vectorizing text...")
    vectorizer = CountVectorizer(stop_words='english')
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)
    
    # Train model
    print("Training Multinomial Naive Bayes model...")
    model = MultinomialNB()
    model.fit(X_train_vec, y_train)
    
    # Evaluation
    print("Evaluating model...")
    y_pred = model.predict(X_test_vec)
    print(f"Accuracy: {accuracy_score(y_test, y_pred)}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Save model and vectorizer
    print("Saving model and vectorizer...")
    joblib.dump(model, 'spam_model.pkl')
    joblib.dump(vectorizer, 'vectorizer.pkl')
    print("Done!")

if __name__ == "__main__":
    train()
