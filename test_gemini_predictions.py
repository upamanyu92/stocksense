#!/usr/bin/env python3
"""
Test script to verify Gemini AI prediction capability
Tests with TCS and Infosys stocks
"""

import sys
import os
sys.path.insert(0, '/Users/commandcenter/pycharmprojects/stocksense')

from datetime import datetime
from app.models.gemini_model import predict_with_details
import yfinance as yf
import json
import pandas as pd

def test_stock_prediction(symbol):
    """Test prediction for a stock using Gemini AI"""
    print(f"\n{'='*80}")
    print(f"Testing Gemini AI Prediction for: {symbol}")
    print(f"{'='*80}")
    print(f"Test Date: {datetime.now().isoformat()}\n")

    try:
        # Fetch current stock data for comparison
        print(f"📊 Fetching current stock data for {symbol}...")
        stock_data = yf.download(symbol, period='5d', progress=False)

        if stock_data.empty:
            print(f"❌ No data found for {symbol}")
            return None

        # Handle potential MultiIndex or Series issues with yfinance
        # yfinance sometimes returns a DataFrame with MultiIndex columns (Ticker, Price)
        if isinstance(stock_data.columns, pd.MultiIndex):
            close_prices = stock_data['Close'][symbol]
        else:
            close_prices = stock_data['Close']
            
        current_price = float(close_prices.iloc[-1])
        previous_price = float(close_prices.iloc[-2])
        price_change = ((current_price - previous_price) / previous_price) * 100

        print(f"  ✅ Current Price: ₹{current_price:.2f}")
        print(f"  ✅ Previous Close: ₹{previous_price:.2f}")
        print(f"  ✅ Change: {price_change:+.2f}%")

        # Get Gemini AI prediction
        print(f"\n🤖 Calling Gemini AI for prediction...")
        print(f"   Processing technical indicators...")
        print(f"   Analyzing market sentiment...")
        print(f"   Generating prediction...\n")

        result = predict_with_details(symbol)

        # Display prediction results
        print(f"{'─'*80}")
        print(f"GEMINI AI PREDICTION RESULTS")
        print(f"{'─'*80}")

        print(f"\n📈 PREDICTION:")
        print(f"   Predicted Price (30 days): ₹{result['predicted_price']:.2f}")
        print(f"   Current Price:             ₹{current_price:.2f}")

        # Calculate expected profit/loss
        if current_price > 0:
            expected_change = ((result['predicted_price'] - current_price) / current_price) * 100
            print(f"   Expected Change:           {expected_change:+.2f}%")

        print(f"\n🎯 CONFIDENCE & DECISION:")
        print(f"   Confidence Score:          {result['confidence']:.2%}")
        print(f"   Decision:                  {result['decision'].upper()}")

        print(f"\n📊 MARKET ANALYSIS:")
        print(f"   Market Sentiment:          {result.get('market_sentiment', 'N/A').upper()}")
        print(f"   Technical Signals:         {result.get('technical_signals', 'N/A').upper()}")
        print(f"   Risk Level:                {result.get('risk_level', 'N/A').upper()}")

        print(f"\n💭 AI REASONING:")
        reasoning = result.get('reasoning', 'No reasoning provided')
        # Wrap text for better readability
        for line in reasoning.split('\n'):
            if line.strip():
                print(f"   {line}")

        print(f"\n⏱️  METADATA:")
        print(f"   Model:                     {result.get('model', 'N/A')}")
        print(f"   Processing Time:           {result.get('processing_time', 'N/A')} seconds")
        print(f"   Timestamp:                 {result.get('timestamp', 'N/A')}")

        print(f"\n{'─'*80}")

        # Accuracy assessment
        print(f"\n📋 ACCURACY ASSESSMENT:")
        if result['confidence'] > 0.8:
            confidence_level = "🟢 HIGH - Gemini AI is very confident in this prediction"
        elif result['confidence'] > 0.6:
            confidence_level = "🟡 MODERATE - Gemini AI has reasonable confidence"
        else:
            confidence_level = "🔴 LOW - Use additional indicators for validation"

        print(f"   {confidence_level}")
        print(f"   Confidence Value: {result['confidence']:.3f}")

        # Decision assessment
        print(f"\n🎯 DECISION ASSESSMENT:")
        decision_map = {
            'accept': '🟢 ACCEPT - Strong signal, proceed with confidence',
            'caution': '🟡 CAUTION - Mixed signals, validate with other indicators',
            'reject': '🔴 REJECT - Insufficient confidence, avoid this trade'
        }
        print(f"   {decision_map.get(result['decision'], 'Unknown decision')}")

        print(f"\n{'='*80}\n")

        return result

    except Exception as e:
        print(f"❌ Error during prediction: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main test function"""
    print("\n" + "="*80)
    print("GEMINI AI STOCK PREDICTION VERIFICATION TEST")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    print("\nTesting Gemini AI's capability to analyze stocks and make predictions")
    print("using technical indicators and AI reasoning.\n")

    # Test stocks
    test_stocks = [
        ('TCS.BO', 'Tata Consultancy Services'),
        ('INFY.BO', 'Infosys Limited')
    ]

    results = {}

    for symbol, company_name in test_stocks:
        print(f"\n🔍 Testing: {company_name} ({symbol})")
        result = test_stock_prediction(symbol)
        results[symbol] = result

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for symbol, company_name in test_stocks:
        if symbol in results and results[symbol]:
            result = results[symbol]
            print(f"\n✅ {company_name} ({symbol})")
            print(f"   Prediction: ₹{result['predicted_price']:.2f}")
            print(f"   Confidence: {result['confidence']:.2%}")
            print(f"   Decision: {result['decision'].upper()}")
        else:
            print(f"\n❌ {company_name} ({symbol}) - Prediction Failed")

    print(f"\nTest completed at: {datetime.now().isoformat()}")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
