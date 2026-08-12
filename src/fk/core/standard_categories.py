import datetime

from fk.core.category import Category


def h3(text: str) -> str:
    return f'#### <h3 style="font-family: Noto Sans, Sans-serif;">{text.upper()}</h3>'


STANDARD_WORKITEM_CATEGORIES = f"""
# 123: 1-2-3 Rule

Split your work into three categories: 

1. A **single** complex task, 
2. **two** secondary tasks for stuff like calls, meetings and helping your colleagues, 
3. and **three** "maintenance" things like cleaning your desk, responding to emails, or filling time sheets.

{h3('When to use it')}

- For daily backlogs,
- if you tend to postpone large complex tasks till the deadline,
- if you can free your entire morning from calls and meetings,
- when you don't like breaking your complex work into subtasks and prefer keeping things as simple as possible.

{h3('In practice')}

1. Decline calls and meetings in the first half of the day. Close your messenger, email, and turn off the phone. Your
productivity in the morning defines whether the rest of the day will succeed or fail. Doing the "complex task" in the 
afternoon is much, MUCH less efficient.

2. Your first and most important work item will take about three hours or 6 pomodoros. 
 * You aim at extracting maximum productivity from the morning session. The "big" item thus doesn't have to be specific 
 -- "Work on the bugs in Jira" would be a valid target, as long as you focus on it. 
 * Be realistic with the estimate for this session. On Monday you might be able to do 7 pomodoros, and on Friday -- 
 5 or even 4. Don't overestimate it, since you still want to complete the remaining things on your list.
 * It is important that you don't plan anything else in between. Do not start working on other tasks before you 
 completed the first one. Protect your Pomodoro twice as hard in the morning.

3. The second group is a good place for your calls, meetings and overall less important tasks. Create two of such items 
and allocate 1 -- 2 pomodoros to each one of them.

4. Everything else goes into the third group. It doesn't deserve more than one, maximum two pomodoros *in total*. This 
way you'll do about 6 + 3 + 1 = 10 pomodoros, which is a comfortable and realistic estimate for an average productive 
day.

5. Before leaving work, take a few minutes to define your 1-2-3 for the next day, so you're ready to hit the ground 
running in the morning.

{h3('Compared to other methods')}

The 1-2-3 and ABCDE are very similar and focus on completing important and unpleasant work first. They both assume that 
*everything* you planned needs to be done.

- 1-2-3 Rule defines the number of tasks (just six for a day!) and their "size". It is slightly easier to use.

- ABCDE Method is less prescriptive and helps you identify work that you can delegate to others or just skip.

Other methods value simplicity, prioritize importance VS urgency, or focus on removing unnecessary work.

{h3('See also')}

[Why You Never Finish Your To-Do Lists at Work (And How to Change That)](https://www.themuse.com/advice/why-you-never-finish-your-todo-lists-at-work-and-how-to-change-that)
by Alex Cavoulacos / The Muse. 1-3-5 is a common variant of 1-2-3, which only differs in the number of tasks.

[The 3-3-3 Method: A Smarter Way to Work (and Live)](https://thinksmarter.substack.com/p/the-3-3-3-method-a-smarter-way-to)
by Emily M Austen. 3-3-3 is a similar technique, which prescribes three hours for the most complex task.

## 1: One large task

5 -- 7 pomodoros

## 2: Two medium tasks

1 pomodoro each

## 3: Three small tasks

1 -- 2 pomodoros for all three

-----------------------------------------------------------------------------------------------------------------------

# ABCDE: ABCDE Method

Assign each work item to one of the five groups: 

1. The task you **A**bsolutely have to complete, 
2. Tasks you should **B**etter complete, 
3. Nice-to-dos with no consequence if you **C**ancel them,
4. Work that you can **D**elegate to others,
5. Activities you should **E**liminate altogether.

{h3('When to use it')}

- For large and high-level backlogs (weekly TODOs, project plans),
- if you don't want to estimate all your tasks at this stage,
- if you work in a team.

{h3('In practice')}

1. To categorize a task as A, B or C, think about it in terms of *consequences*. A will have major, B -- minor, and 
C -- no consequence if not done.

2. The key to making this method work is for you to discipline yourself to start immediately on your A task. Try to do 
it in the morning, or as early as possible. Use your willpower to eat the whole frog and don’t stop until it’s finished 
completely.

3. You can categorize a task using several methods. For example, you can use ABCDE in your Project backlog, and then 
drag tasks from there into your daily Pomodoro backlog, where you group them using 1-2-3 method.

4. Every Friday move "D" and "E" tasks from daily backlogs to a "Trash" backlog, cleaning it up first.

{h3('Compared to other methods')}

The 1-2-3 and ABCDE are very similar and focus on completing important and unpleasant work first. They both assume that 
*everything* you planned needs to be done.

- 1-2-3 Rule defines the number of tasks (just six for a day!) and their "size". It is slightly easier to use.

- ABCDE Method is less prescriptive and helps you identify work that you can delegate to others or just skip.

Other methods value simplicity, prioritize importance VS urgency, or focus on removing unnecessary work.

{h3('See also')}

[The ABCD List Technique for Setting Priorities](https://www.briantracy.com/blog/time-management/the-abcde-list-technique-for-setting-priorities/)
by Brian Tracy.

## A: A - Most important

**"A" Items Are Most Important**

An A item is defined as something that is very important. This is something that you must do.

This is a task for which there can be serious consequences if you fail to do it. Consequences such as not visiting a key 
customer or not finishing a report for your boss that she needs for an upcoming board meeting.

These are the frogs of your life.

## B: B - Important

**"B" Items Only Have Minor Consequences**

A B item is defined as a task that you should do. But it only has mild consequences.

These are the tadpoles of your work life. This means that someone may be unhappy or inconvenienced if you don’t do it, 
but it is nowhere as important as an A task. Returning an unimportant telephone message or reviewing your email would be 
a B task.

The rule is that you should never do a B task when there is an A task left undone. You should never be distracted by a 
tadpole when there is a big frog sitting there waiting to be eaten.

## C: C - Nice to do

**"C" Tasks Have No Consequences**

A C task is something that would be nice to do, but for which there are no consequences at all, whether you do it or 
not.

C tasks include phoning a friend, having coffee or lunch with a coworker or completing some personal business during 
work hours. This sort of activity has no effect at all on your work life.

As a rule, you can never complete a C task when there are B or A tasks left undone.

## D: D - Delegate

**"D" for Delegate**

A D activity is something that you can delegate to someone else.

The rule is that you should delegate everything that you possibly can to other people. This frees up more time for you 
to engage in your A activities. Your A tasks and their completion, largely determine the entire course of your career.

## E: E - Eliminate

**"E" for Eliminate**

An E activity is something that you should eliminate altogether.

After all, you can only get your time under control if you stop doing things that are no longer necessary for you to do.

-----------------------------------------------------------------------------------------------------------------------

# Eisenhower: Eisenhower Matrix

> *"I have two kinds of problems: the urgent and the important. The urgent are not important, and the important are 
never urgent."* - Dwight D. Eisenhower

Split your tasks into four quadrants:

1. **Urgent and Important** (with deadlines or consequences),

2. **Important** but Not Urgent (with unclear deadlines that contribute to long-term success),

3. **Urgent** but Not Important (require your attention, but do not have deadlines or consequences),

4. Not Urgent and Not Important (unnecessary, distractions, and time-wasters).

{h3('When to use it')}

- If you have more than a couple of unplanned items every day,
- if you feel that you do too much fire fighting,
- if you work hard but don't progress towards your goal,
- for daily backlogs.

{h3('In practice')}

- When an unplanned / urgent task arrives, do not start working on it immediately. Record and classify it quickly. 
Most importantly, protect your current Pomodoro!

- Postpone new Urgent and Not Important tasks at least till next day. Try to find someone else to work on it.

- Every Friday move *Not Urgent and Not Important* tasks from daily backlogs to a "Trash" backlog, cleaning it up first.

{h3('Compared to other methods')}

Eisenhower matrix distinguishes between importance and urgency, prioritizing the former. It implies that a bunch of 
tasks in your backlog will stay incomplete, and that's OK. In this sense it is similar to Pareto principle and 
Must-Should-Want.

The matrix doesn't say how many tasks you should have, or how much time you must spend on each one.

Other methods like 1-2-3 and ABCDE are more prescriptive and focus on the execution, assuming that you need to complete
*everything* in your daily backlog.

{h3('See also')}

[The urgent and the important](https://www.rtalbert.org/blog-archive/index.php/2019/10/14/the-urgent-and-the-important)
by Robert Talbert, Ph.D.

## UI: Urgent and Important

Tasks that are urgent and important are the highest priority and should be done ASAP. They are automatic candidates for 
the Most Important Thing (MIT) list for a given day.

Example: The professor's unit recommendation for Promotion happens to be due on Friday, so this is both urgent and 
important --- that's an MIT on my list for tomorrow and has a two-hour block in my calendar tomorrow morning all by 
itself.

## NUI: Important but Not Urgent

Tasks that are important but not urgent come second. These need to be done; schedule time during the week to do them.

Example: Reading the article about the course redesign is important, but not urgent --- schedule one pomodoro during the 
week to read and take notes on it, and get it done this week.

## UNI: Urgent but Not Important

Tasks that are urgent but not important are third. Delegate these if possible. Otherwise schedule time for them, but 
not at the expense of the important stuff.

For example, suppose I get an email from a student who's having trouble with their professor and wants an appointment 
this week. I need to act on this, but it is not something I would categorize as strategically important in the sense of 
serving a long-term goal. So it's "urgent but not important". I'll probably delegate this by telling the student to set 
up an appointment with me through our office staff.

## NUNI: Not Urgent and Not Important

Tasks that are neither urgent nor important get whatever time is left over. 

-----------------------------------------------------------------------------------------------------------------------

# Pareto: Pareto Principle

Use two simple categories and focus on completing work items from the first group:

1. 20% Effort, 80% Outcomes
2. 80% Effort, 20% Outcomes

{h3('When to use it')}

- If you work hard but don't progress towards your goal,
- if you want the simplest method,
- for any backlogs.

{h3('In practice')}

- In reality most of the tasks will fall into a ~50:50 gray zone. Consider them as "80% effort" by default. Aim at 1:5
ratio between the first and second groups.

- Automatically postpone new tasks from the second group at least till next day.

- Every Friday move *80% Effort, 20% Outcome* tasks from daily backlogs to a "Trash" backlog, cleaning it up first.

- When we act less, we think more and better. Do not reinvest the saved time in work. Use it to reflect, relax and 
self-improve.

{h3('Compared to other methods')}

With just two categories, Pareto principle is the simplest categorization method possible.

{h3('See also')}

[How to Work Less, Live More, and Be More Effective](https://www.psychologytoday.com/gb/blog/the-art-of-self-improvement/202312/work-less-live-more-and-be-more-effective)
by Anna Katharina Schaffner Ph.D:

> *"If we double our time on our top 20 percent of activities, we can work a two-day week and achieve 60 percent more 
than now."*

[Warren Buffett's 5/25 Rule](https://jamesclear.com/buffett-focus) - a similar method which prescribes the number of 
tasks. It works best for strategic planning, monthly and weekly backlogs.

## 20: 20% Effort, 80% Outcomes

Which of my work activities matters most? What are the 20 percent that leads to my successes?

## 80: 80% Effort, 20% Outcomes

Which of the non-generative activities can I minimize? Which activities can I say no to in the future?

-----------------------------------------------------------------------------------------------------------------------

# MSW: Must, Should, Want

Fill your backlog for the day by asking yourself three questions:

- What **must** I do to create the most impact today?
- What **should** I do to build a better future?
- What do I **want** to do so that I may enjoy today and life more completely?

{h3('When to use it')}

- If you are dissatisfied with the results of your work,
- if other techniques seem annoyingly prescriptive,
- for daily and weekly backlogs,
- for personal projects,
- for budgeting and organizing your shopping lists.

{h3('In practice')}

- Relative priorities within "should do" and "want" classes affect decisions on trade-in and trade-out.

- It is important to distinguish between the "Must do" and the rest, but less important to distinguish between "Should 
do" and "Want". 

- You can get an extra prioritization dimension by ordering tasks within each category.

- Re-evaluate the items regularly, as your priorities change. Do NOT discard your "wants" automatically.

- Try to start with only one task in each category, the results might surprise you.

{h3('Compared to other methods')}

This method must be the easiest to categorize your tasks in practice. It gives you maximum freedom and doesn't tell
you what to do with the tasks once you grouped them.

{h3('See also')}

[Get the Best Start](https://web.archive.org/web/20140507073715/http://www.jayshirley.com/blog/2014/3/31/best-start-of-the-day)
by Jay Shirley.

[MoSCoW Method](https://en.wikipedia.org/wiki/MoSCoW_method) - a more formal and sophisticated *project* prioritization 
technique. You can use it for organizing bigger backlogs.

[Fast-track: a RAD approach](https://archive.org/details/fasttrackradappr0000cleg/mode/2up) by Dai Clegg.

## M: I must...

What must I do to create the most impact today?

Musts are your true non-negotiables. These include things with deadlines, commitments, and anything that would cause a 
real problem tomorrow if it’s not done. 

It is easy to put all your tasks in this list. Don't do it. The ideal number of tasks in this list is 1 -- 2.

## S: I should...

What should I do to build a better future?

Shoulds are important, useful, and responsible tasks. They make things better, smoother, or easier, but they aren’t an 
immediate concern. 

## W: I want to...

What do I want to do so that I may enjoy today and life more completely?

Wants are things you actually want to do. Creative work. Personal projects. Nice-to-haves that tend to get pushed aside 
when the day fills up.

It's too easy to ignore this, especially when you work under stress. This leads to overfocus, which reduces productivity
in the long term.

-----------------------------------------------------------------------------------------------------------------------
"""


# A simple state machine to initialize categories and subcategories
def get_standard_workitem_categories(root: Category, now: datetime.datetime) -> Category:
    wg = Category('Item Groups', '#workitem_groups', True, "Info", root, now)

    info = list()
    category: Category
    subcategory: Category = None
    for l in STANDARD_WORKITEM_CATEGORIES.split('\n'):
        l = l.strip()
        if l.startswith('# '):
            uid, name = l[2:].split(': ')
            uid = f'#wg_{uid}'
            category = Category(name, uid, True, "Info", wg, now)
            wg[uid] = category
        elif l.startswith('## '):
            txt = "\n".join(info).strip()
            if subcategory is None:
                category._info = txt
            else:
                subcategory._info = txt
            uid, name = l[3:].split(': ')
            uid = f'{category.get_uid()}_{uid}'
            subcategory = Category(name, uid, True, "Info", category, now)
            category[uid] = subcategory
            info.clear()
        elif l.startswith('---'):
            txt = "\n".join(info).strip()
            if subcategory is None:
                category._info = txt
            else:
                subcategory._info = txt
            info.clear()
            subcategory = None
            category = None
            continue
        else:
            info.append(l)

    return wg


def create_system_categories(root: Category, now: datetime.datetime) -> None:
    root['#workitem_groups'] = get_standard_workitem_categories(root, now)
    root['#workitem_shares'] = Category('Workitem Shares', '#workitem_shares', True, "Info", root, now)
    root['#workitem_integrations'] = Category('Workitem Integrations', '#workitem_integrations', True, "Info", root, now)
    root['#workitem_tags'] = Category('Workitem Tags', '#workitem_tags', True, "Info", root, now)

    root['#backlog_groups'] = Category('Backlog Groups', '#backlog_groups', True, "Info", root, now)
    root['#backlog_shares'] = Category('Backlog Shares', '#backlog_shares', True, "Info", root, now)
    root['#backlog_integrations'] = Category('Backlog Integrations', '#backlog_integrations', True, "Info", root, now)
    root['#backlog_tags'] = Category('Backlog Tags', '#backlog_tags', True, "Info", root, now)


