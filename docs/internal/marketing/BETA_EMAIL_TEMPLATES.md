# Beta Email Templates - QA-FRAMEWORK

**Purpose:** Professional email templates for beta tester communication
**Version:** 1.0
**Last Updated:** 2026-02-28

---

## 📧 Template 1: Welcome Email

### Subject Line
```
Welcome to QA-FRAMEWORK Beta! 🚀
```

### HTML Version
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to QA-FRAMEWORK Beta</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9fafb;
        }
        .container {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo h1 {
            color: #6366f1;
            font-size: 28px;
            margin: 0;
        }
        .hero {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            text-align: center;
        }
        .hero h2 {
            margin: 0 0 10px 0;
            font-size: 24px;
        }
        .hero p {
            margin: 0;
            opacity: 0.9;
        }
        .cta-button {
            display: inline-block;
            background-color: #6366f1;
            color: white;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
            transition: background-color 0.3s;
        }
        .cta-button:hover {
            background-color: #4f46e5;
        }
        .features {
            background-color: #f3f4f6;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .feature-item {
            margin: 10px 0;
            padding-left: 25px;
            position: relative;
        }
        .feature-item:before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #10b981;
            font-weight: bold;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 14px;
        }
        .social-links {
            margin: 15px 0;
        }
        .social-links a {
            margin: 0 10px;
            color: #6366f1;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>🎯 QA-FRAMEWORK</h1>
        </div>
        
        <div class="hero">
            <h2>Welcome to the Beta Program! 🎉</h2>
            <p>Hi {{name}}, you're in! Get ready to revolutionize your testing workflow.</p>
        </div>
        
        <p>Thank you for joining the QA-FRAMEWORK beta program. You're among the first to experience AI-powered testing that actually works.</p>
        
        <div class="features">
            <h3>What You Get:</h3>
            <div class="feature-item"><strong>Unlimited tests</strong> during beta period</div>
            <div class="feature-item"><strong>AI self-healing</strong> - tests adapt to UI changes</div>
            <div class="feature-item"><strong>Smart generation</strong> - create tests from requirements</div>
            <div class="feature-item"><strong>Flaky detection</strong> - never chase false failures again</div>
            <div class="feature-item"><strong>Priority support</strong> - direct line to our team</div>
        </div>
        
        <p style="text-align: center;">
            <a href="{{dashboard_url}}" class="cta-button">Access Your Dashboard →</a>
        </p>
        
        <p><strong>Quick Start:</strong></p>
        <ol>
            <li>Log in to your dashboard</li>
            <li>Connect your first test suite</li>
            <li>Watch AI do its magic</li>
            <li>Share your feedback!</li>
        </ol>
        
        <p><strong>Need help?</strong> Reply to this email or join our <a href="{{discord_url}}">Discord community</a>.</p>
        
        <div class="footer">
            <div class="social-links">
                <a href="{{twitter_url}}">Twitter</a>
                <a href="{{linkedin_url}}">LinkedIn</a>
                <a href="{{github_url}}">GitHub</a>
            </div>
            <p>© 2026 QA-FRAMEWORK. All rights reserved.</p>
            <p>You're receiving this because you signed up for our beta program.</p>
            <p><a href="{{unsubscribe_url}}">Unsubscribe</a> | <a href="{{preferences_url}}">Email Preferences</a></p>
        </div>
    </div>
</body>
</html>
```

### Plain Text Version
```
WELCOME TO QA-FRAMEWORK BETA! 🎉

Hi {{name}},

Thank you for joining the QA-FRAMEWORK beta program! You're among the first to experience AI-powered testing.

WHAT YOU GET:
✓ Unlimited tests during beta period
✓ AI self-healing - tests adapt to UI changes
✓ Smart generation - create tests from requirements
✓ Flaky detection - never chase false failures again
✓ Priority support - direct line to our team

QUICK START:
1. Log in to your dashboard: {{dashboard_url}}
2. Connect your first test suite
3. Watch AI do its magic
4. Share your feedback!

NEED HELP?
Reply to this email or join our Discord: {{discord_url}}

---
© 2026 QA-FRAMEWORK
Unsubscribe: {{unsubscribe_url}}
```

---

## 📧 Template 2: Onboarding Email

### Subject Line
```
Getting Started with QA-FRAMEWORK (Your 5-Minute Guide)
```

### HTML Version
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Getting Started with QA-FRAMEWORK</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9fafb;
        }
        .container {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        .step {
            background-color: #f3f4f6;
            border-left: 4px solid #6366f1;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }
        .step-number {
            background-color: #6366f1;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 10px;
        }
        .code-block {
            background-color: #1a1a1a;
            color: #10b981;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            overflow-x: auto;
            margin: 15px 0;
        }
        .cta-button {
            display: inline-block;
            background-color: #6366f1;
            color: white;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }
        .video-link {
            display: inline-flex;
            align-items: center;
            background-color: #fef3c7;
            padding: 12px 20px;
            border-radius: 6px;
            text-decoration: none;
            color: #92400e;
            margin: 10px 0;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Let's Get You Started</h1>
        
        <p>Hi {{name}},</p>
        <p>Ready to transform your testing workflow? Here's your quick-start guide to QA-FRAMEWORK.</p>
        
        <a href="{{video_tutorial_url}}" class="video-link">
            📺 Watch the 3-minute demo video
        </a>
        
        <div class="step">
            <h3><span class="step-number">1</span> Install the CLI</h3>
            <div class="code-block">pip install qa-framework-cli</div>
            <p>Or use our REST API directly if you prefer.</p>
        </div>
        
        <div class="step">
            <h3><span class="step-number">2</span> Connect Your Test Suite</h3>
            <div class="code-block">qa-framework init --framework {{framework}}</div>
            <p>Supports: Pytest, Cypress, Playwright, Jest, and more.</p>
        </div>
        
        <div class="step">
            <h3><span class="step-number">3</span> Run Your First Analysis</h3>
            <div class="code-block">qa-framework analyze --path ./tests</div>
            <p>We'll detect flaky tests and suggest improvements automatically.</p>
        </div>
        
        <div class="step">
            <h3><span class="step-number">4</span> Enable AI Self-Healing</h3>
            <div class="code-block">qa-framework heal --enable</div>
            <p>Your tests will now adapt when UI elements change.</p>
        </div>
        
        <p style="text-align: center;">
            <a href="{{dashboard_url}}" class="cta-button">Open Dashboard →</a>
        </p>
        
        <h3>📚 Resources</h3>
        <ul>
            <li><a href="{{docs_url}}">Documentation</a></li>
            <li><a href="{{api_docs_url}}">API Reference</a></li>
            <li><a href="{{examples_url}}">Code Examples</a></li>
            <li><a href="{{discord_url}}">Community Support</a></li>
        </ul>
        
        <p><strong>Questions?</strong> Reply to this email or book a <a href="{{calendly_url}}">15-min call</a> with our team.</p>
        
        <div class="footer">
            <p>© 2026 QA-FRAMEWORK | <a href="{{unsubscribe_url}}">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
```

### Plain Text Version
```
GETTING STARTED WITH QA-FRAMEWORK

Hi {{name}},

Here's your 5-minute guide to transforming your testing workflow.

📺 Watch the demo: {{video_tutorial_url}}

STEP 1: Install the CLI
pip install qa-framework-cli

STEP 2: Connect Your Test Suite
qa-framework init --framework {{framework}}
(Supports: Pytest, Cypress, Playwright, Jest)

STEP 3: Run Your First Analysis
qa-framework analyze --path ./tests

STEP 4: Enable AI Self-Healing
qa-framework heal --enable

RESOURCES:
- Documentation: {{docs_url}}
- API Reference: {{api_docs_url}}
- Examples: {{examples_url}}
- Community: {{discord_url}}

QUESTIONS?
Reply to this email or book a call: {{calendly_url}}

Dashboard: {{dashboard_url}}

---
© 2026 QA-FRAMEWORK
Unsubscribe: {{unsubscribe_url}}
```

---

## 📧 Template 3: Weekly Progress Update

### Subject Line
```
Your Weekly QA-FRAMEWORK Stats 📊
```

### HTML Version
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Progress Update</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9fafb;
        }
        .container {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-number {
            font-size: 32px;
            font-weight: bold;
            color: #6366f1;
            margin: 0;
        }
        .stat-label {
            color: #6b7280;
            font-size: 14px;
            margin: 5px 0 0 0;
        }
        .highlight {
            background-color: #d1fae5;
            border-left: 4px solid #10b981;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }
        .cta-button {
            display: inline-block;
            background-color: #6366f1;
            color: white;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Your Weekly Stats</h1>
        
        <p>Hi {{name}},</p>
        <p>Here's what happened with your tests this week:</p>
        
        <div class="stats-grid">
            <div class="stat-card">
                <p class="stat-number">{{tests_run}}</p>
                <p class="stat-label">Tests Run</p>
            </div>
            <div class="stat-card">
                <p class="stat-number">{{pass_rate}}%</p>
                <p class="stat-label">Pass Rate</p>
            </div>
            <div class="stat-card">
                <p class="stat-number">{{tests_healed}}</p>
                <p class="stat-label">Tests Healed</p>
            </div>
            <div class="stat-card">
                <p class="stat-number">{{flaky_detected}}</p>
                <p class="stat-label">Flaky Detected</p>
            </div>
        </div>
        
        <div class="highlight">
            <strong>🎉 Highlight:</strong> {{highlight_message}}
        </div>
        
        <h3>📈 Improvements This Week</h3>
        <ul>
            <li>Test maintenance time: <strong>down {{time_saved}}%</strong></li>
            <li>False failure rate: <strong>down {{false_failure_reduction}}%</strong></li>
            <li>Test coverage: <strong>up {{coverage_increase}}%</strong></li>
        </ul>
        
        <h3>🔥 Recommended Actions</h3>
        <ol>
            <li>{{recommendation_1}}</li>
            <li>{{recommendation_2}}</li>
            <li>{{recommendation_3}}</li>
        </ol>
        
        <p style="text-align: center;">
            <a href="{{dashboard_url}}" class="cta-button">View Detailed Report →</a>
        </p>
        
        <div class="footer">
            <p>© 2026 QA-FRAMEWORK | <a href="{{unsubscribe_url}}">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
```

### Plain Text Version
```
YOUR WEEKLY QA-FRAMEWORK STATS 📊

Hi {{name}},

Here's what happened with your tests this week:

TESTS RUN: {{tests_run}}
PASS RATE: {{pass_rate}}%
TESTS HEALED: {{tests_healed}}
FLAKY DETECTED: {{flaky_detected}}

🎉 HIGHLIGHT: {{highlight_message}}

IMPROVEMENTS THIS WEEK:
- Test maintenance time: down {{time_saved}}%
- False failure rate: down {{false_failure_reduction}}%
- Test coverage: up {{coverage_increase}}%

RECOMMENDED ACTIONS:
1. {{recommendation_1}}
2. {{recommendation_2}}
3. {{recommendation_3}}

View detailed report: {{dashboard_url}}

---
© 2026 QA-FRAMEWORK
Unsubscribe: {{unsubscribe_url}}
```

---

## 📧 Template 4: Feedback Request

### Subject Line
```
Quick Question About Your QA-FRAMEWORK Experience 💬
```

### HTML Version
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feedback Request</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9fafb;
        }
        .container {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        .feedback-box {
            background-color: #fef3c7;
            padding: 25px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .rating-option {
            display: inline-block;
            width: 40px;
            height: 40px;
            line-height: 40px;
            text-align: center;
            background-color: #f3f4f6;
            border-radius: 50%;
            margin: 0 5px;
            text-decoration: none;
            color: #1a1a1a;
            font-weight: bold;
        }
        .rating-option:hover {
            background-color: #6366f1;
            color: white;
        }
        .cta-button {
            display: inline-block;
            background-color: #6366f1;
            color: white;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }
        .incentive {
            background: linear-gradient(135deg, #818cf8 0%, #6366f1 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>💬 We'd Love Your Feedback</h1>
        
        <p>Hi {{name}},</p>
        <p>You've been using QA-FRAMEWORK for {{days_using}} days now, and we'd love to hear about your experience.</p>
        
        <div class="feedback-box">
            <h3 style="margin-top: 0;">How likely are you to recommend QA-FRAMEWORK?</h3>
            <p style="text-align: center;">
                <a href="{{rating_url}}/1" class="rating-option">1</a>
                <a href="{{rating_url}}/2" class="rating-option">2</a>
                <a href="{{rating_url}}/3" class="rating-option">3</a>
                <a href="{{rating_url}}/4" class="rating-option">4</a>
                <a href="{{rating_url}}/5" class="rating-option">5</a>
                <a href="{{rating_url}}/6" class="rating-option">6</a>
                <a href="{{rating_url}}/7" class="rating-option">7</a>
                <a href="{{rating_url}}/8" class="rating-option">8</a>
                <a href="{{rating_url}}/9" class="rating-option">9</a>
                <a href="{{rating_url}}/10" class="rating-option">10</a>
            </p>
            <p style="text-align: center; color: #6b7280; font-size: 14px;">
                1 = Not likely at all | 10 = Extremely likely
            </p>
        </div>
        
        <div class="incentive">
            <h3 style="margin: 0 0 10px 0;">🎁 Get 3 Months Free Pro!</h3>
            <p style="margin: 0;">Complete our 5-minute survey and get extended Pro access when we launch.</p>
        </div>
        
        <p style="text-align: center;">
            <a href="{{survey_url}}" class="cta-button">Take the Survey →</a>
        </p>
        
        <p>Or simply reply to this email with your thoughts. We read every response personally.</p>
        
        <h3>What We're Looking For:</h3>
        <ul>
            <li>What's working well for you?</li>
            <li>What could be improved?</li>
            <li>Any features you'd like to see?</li>
            <li>Any bugs or issues?</li>
        </ul>
        
        <p>Thank you for helping us build a better product!</p>
        
        <div class="footer">
            <p>© 2026 QA-FRAMEWORK | <a href="{{unsubscribe_url}}">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
```

### Plain Text Version
```
WE'D LOVE YOUR FEEDBACK 💬

Hi {{name}},

You've been using QA-FRAMEWORK for {{days_using}} days now, and we'd love to hear about your experience.

HOW LIKELY ARE YOU TO RECOMMEND QA-FRAMEWORK?
Rate us 1-10: {{rating_url}}

🎁 BONUS: Get 3 Months Free Pro!
Complete our 5-minute survey and get extended Pro access when we launch.
Survey: {{survey_url}}

WHAT WE'RE LOOKING FOR:
- What's working well for you?
- What could be improved?
- Any features you'd like to see?
- Any bugs or issues?

Or simply reply to this email with your thoughts. We read every response personally.

Thank you for helping us build a better product!

---
© 2026 QA-FRAMEWORK
Unsubscribe: {{unsubscribe_url}}
```

---

## 📧 Template 5: Feature Announcement

### Subject Line
```
New Feature: {{feature_name}} 🚀
```

### HTML Version
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Feature Announcement</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9fafb;
        }
        .container {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        .feature-hero {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            padding: 40px 30px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 30px;
        }
        .feature-hero h1 {
            margin: 0;
            font-size: 28px;
        }
        .feature-hero p {
            margin: 10px 0 0 0;
            opacity: 0.95;
        }
        .benefit-card {
            background-color: #f3f4f6;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #6366f1;
        }
        .cta-button {
            display: inline-block;
            background-color: #6366f1;
            color: white;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }
        .code-example {
            background-color: #1a1a1a;
            color: #10b981;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            overflow-x: auto;
            margin: 20px 0;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="feature-hero">
            <h1>🚀 New: {{feature_name}}</h1>
            <p>{{feature_tagline}}</p>
        </div>
        
        <p>Hi {{name}},</p>
        <p>We're excited to announce a powerful new feature that will make your testing even more efficient!</p>
        
        <h2>What's New</h2>
        <p>{{feature_description}}</p>
        
        <div class="benefit-card">
            <h3 style="margin-top: 0;">✨ Key Benefits</h3>
            <ul style="margin-bottom: 0;">
                <li>{{benefit_1}}</li>
                <li>{{benefit_2}}</li>
                <li>{{benefit_3}}</li>
            </ul>
        </div>
        
        <h3>See It in Action</h3>
        <div class="code-example">
{{code_example}}
        </div>
        
        <h3>How to Use It</h3>
        <ol>
            <li>{{step_1}}</li>
            <li>{{step_2}}</li>
            <li>{{step_3}}</li>
        </ol>
        
        <p style="text-align: center;">
            <a href="{{feature_url}}" class="cta-button">Try It Now →</a>
        </p>
        
        <p><strong>📚 Documentation:</strong> <a href="{{docs_url}}">{{docs_url}}</a></p>
        
        <p>As always, we'd love to hear your feedback. Reply to this email with your thoughts!</p>
        
        <div class="footer">
            <p>© 2026 QA-FRAMEWORK | <a href="{{unsubscribe_url}}">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
```

### Plain Text Version
```
NEW FEATURE: {{feature_name}} 🚀

{{feature_tagline}}

Hi {{name}},

We're excited to announce a powerful new feature!

WHAT'S NEW:
{{feature_description}}

KEY BENEFITS:
✓ {{benefit_1}}
✓ {{benefit_2}}
✓ {{benefit_3}}

SEE IT IN ACTION:
{{code_example}}

HOW TO USE IT:
1. {{step_1}}
2. {{step_2}}
3. {{step_3}}

Try it now: {{feature_url}}
Documentation: {{docs_url}}

As always, we'd love to hear your feedback. Reply to this email!

---
© 2026 QA-FRAMEWORK
Unsubscribe: {{unsubscribe_url}}
```

---

## 📧 Template 6: Beta Thank You

### Subject Line
```
Thank You for an Amazing Beta Journey! 🙏
```

### HTML Version
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thank You - Beta Program</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9fafb;
        }
        .container {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        .hero {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            padding: 40px 30px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 30px;
        }
        .hero h1 {
            margin: 0;
            font-size: 28px;
        }
        .stats-box {
            background-color: #f3f4f6;
            padding: 25px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }
        .stat {
            display: inline-block;
            margin: 0 20px;
        }
        .stat-number {
            font-size: 32px;
            font-weight: bold;
            color: #6366f1;
            margin: 0;
        }
        .stat-label {
            color: #6b7280;
            font-size: 14px;
        }
        .offer-box {
            background-color: #d1fae5;
            border: 2px solid #10b981;
            padding: 25px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }
        .offer-box h3 {
            margin-top: 0;
            color: #065f46;
        }
        .cta-button {
            display: inline-block;
            background-color: #6366f1;
            color: white;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }
        .testimonial-box {
            background-color: #fef3c7;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            font-style: italic;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <h1>🙏 Thank You, {{name}}!</h1>
            <p style="margin: 10px 0 0 0;">You helped shape QA-FRAMEWORK</p>
        </div>
        
        <p>The beta period has officially ended, and we couldn't have done it without you!</p>
        
        <div class="stats-box">
            <h3>Your Impact</h3>
            <div class="stat">
                <p class="stat-number">{{tests_run}}</p>
                <p class="stat-label">Tests Run</p>
            </div>
            <div class="stat">
                <p class="stat-number">{{bugs_found}}</p>
                <p class="stat-label">Bugs Found</p>
            </div>
            <div class="stat">
                <p class="stat-number">{{feedback_given}}</p>
                <p class="stat-label">Feedback Items</p>
            </div>
        </div>
        
        <h3>🎉 What You Helped Us Build</h3>
        <ul>
            <li><strong>Self-healing tests</strong> - Your feedback improved accuracy by 34%</li>
            <li><strong>Flaky detection</strong> - 12 of your suggestions were implemented</li>
            <li><strong>Test generation</strong> - You helped us refine the AI models</li>
        </ul>
        
        <div class="offer-box">
            <h3>🎁 Exclusive Beta Tester Offer</h3>
            <p style="font-size: 18px; margin: 15px 0;"><strong>50% OFF</strong> Pro Plan for Life</p>
            <p style="margin-bottom: 0;">Use code: <strong>BETA-{{user_code}}</strong></p>
            <p style="font-size: 14px; margin-top: 5px;">Valid until {{expiry_date}}</p>
        </div>
        
        <p style="text-align: center;">
            <a href="{{upgrade_url}}" class="cta-button">Claim Your Discount →</a>
        </p>
        
        <div class="testimonial-box">
            <p>"{{testimonial}}"</p>
            <p style="margin-bottom: 0; text-align: right;">— {{user_name}}, {{company}}</p>
        </div>
        
        <h3>What's Next?</h3>
        <ol>
            <li>Check your email for the exclusive discount code</li>
            <li>Upgrade to Pro before {{expiry_date}}</li>
            <li>Continue enjoying AI-powered testing!</li>
        </ol>
        
        <p>Thank you for being part of our journey. We can't wait to see what you'll build next!</p>
        
        <div class="footer">
            <p>© 2026 QA-FRAMEWORK | <a href="{{unsubscribe_url}}">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
```

### Plain Text Version
```
THANK YOU FOR AN AMAZING BETA JOURNEY! 🙏

Hi {{name}},

The beta period has officially ended, and we couldn't have done it without you!

YOUR IMPACT:
- Tests Run: {{tests_run}}
- Bugs Found: {{bugs_found}}
- Feedback Items: {{feedback_given}}

WHAT YOU HELPED US BUILD:
✓ Self-healing tests - Your feedback improved accuracy by 34%
✓ Flaky detection - 12 of your suggestions were implemented
✓ Test generation - You helped us refine the AI models

🎁 EXCLUSIVE BETA TESTER OFFER:
50% OFF Pro Plan for Life!
Use code: BETA-{{user_code}}
Valid until: {{expiry_date}}

Claim your discount: {{upgrade_url}}

"{{testimonial}}"
— {{user_name}}, {{company}}

WHAT'S NEXT:
1. Check your email for the exclusive discount code
2. Upgrade to Pro before {{expiry_date}}
3. Continue enjoying AI-powered testing!

Thank you for being part of our journey. We can't wait to see what you'll build next!

---
© 2026 QA-FRAMEWORK
Unsubscribe: {{unsubscribe_url}}
```

---

## 🔧 Personalization Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `{{name}}` | User's first name | John |
| `{{company}}` | Company name | Acme Corp |
| `{{email}}` | User's email | john@acme.com |
| `{{dashboard_url}}` | Dashboard link | https://qa-framework.railway.app/dashboard |
| `{{framework}}` | Test framework | pytest, cypress, playwright |
| `{{days_using}}` | Days since signup | 14 |
| `{{tests_run}}` | Total tests run | 1,247 |
| `{{pass_rate}}` | Test pass rate | 94.5 |
| `{{tests_healed}}` | Auto-healed tests | 23 |
| `{{flaky_detected}}` | Flaky tests found | 7 |
| `{{unsubscribe_url}}` | Unsubscribe link | https://.../unsubscribe |
| `{{discord_url}}` | Discord invite | https://discord.gg/... |
| `{{docs_url}}` | Documentation | https://docs.qa-framework.com |

---

## 📋 Email Sequence Timeline

| Day | Email | Purpose |
|-----|-------|---------|
| 0 | Welcome | Immediate after signup |
| 1 | Onboarding | Guide to getting started |
| 7 | Feedback Request | First check-in |
| 14 | Weekly Stats | Show value |
| 21 | Feature Announcement | Introduce new capability |
| 30 | Feedback Request | NPS survey |
| 60 | Beta Thank You | End of beta + offer |

---

*Last updated: 2026-02-28*
*Version: 1.0*
*Author: Alfred (AI Assistant)*
