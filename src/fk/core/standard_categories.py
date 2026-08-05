import datetime

from fk.core.category import Category


def h3(text: str) -> str:
    return f'#### <h3 style="font-family: Noto Sans, Sans-serif;">{text.upper()}</h3>'


STANDARD_WORKITEM_CATEGORIES = f"""
# 123: 1-2-3 Rule

Split your work into three categories: 

1. A **single** complex task, 
2. two secondary tasks for stuff like calls, meetings and helping your colleagues, 
3. and three little "maintenance" things like cleaning your desk, responding to emails, or filling time sheets.

{h3('When to use it')}

- For daily backlogs,
- if you tend to postpone large complex tasks till the deadline,
- if you can free your entire morning from calls, meetings, etc.,
- when you don't like breaking your complex work into subtasks and prefer keeping things as simple as possible.

{h3('In practice')}

1. Decline calls and meetings in the first half of the day. Close your messenger, email, turn off the phone, etc. Your
productivity in the morning defines whether the rest of the day will succeed or fail. Doing the "complex task" in the 
afternoon is much, MUCH less efficient.

2. Your first and most important work item will take about three hours or 6 pomodoros. 
 * You aim at extracting maximum productivity from the morning session. The "big" item thus doesn't have to be specific 
 -- "Work on the bugs in Jira" would be a valid target, as long as you focus on it. 
 * Be realistic with the estimate for this session. On Monday you might be able to do 7 pomodoros, and on Friday -- 
 only 5. Don't overestimate it, since you still want to complete the remaining things on your list.
 * It is important that you don't plan anything else in between. Do not start working on other tasks before you 
 completed the first one. Protect your Pomodoro twice as hard in the morning.

3. The second group is a good place for your calls, meetings and overall less important tasks. Create two of such items 
and allocate 1 -- 2 pomodoros to each one of them.

4. Everything else goes into the third group. It doesn't deserve more than one, maximum two pomodoros *in total*. This 
way you'll do about 6 + 3 + 1 = 10 pomodoros, which is a comfortable and realistic estimate for an average productive 
day.

5. Before leaving work, take a few minutes to define your 1-2-3 for the next day, so you're ready to hit the ground 
running in the morning.

{h3('See also')}

[Follow the 1-3-5 Rule](https://www.themuse.com/advice/why-you-never-finish-your-todo-lists-at-work-and-how-to-change-that)

(C) Alex Cavoulacos / The Muse

## 1: One large task (important, big-win task you must complete)

5 -- 7 pomodoros

## 2: Two medium tasks (relatively important tasks you need to complete)

1 pomodoro each

## 3: Three small tasks (tasks you’d like to complete)

1 -- 2 pomodoros for all three

-----------------------------------------------------------------------------------------------------------------------

# ABCDE: ABCDE Method

This method helps you prioritize work items. It doesn't care about tasks count, duration or complexity. Split your work 
into five categories: 

1. A: The most important, critical tasks, 
2. B: Tasks with only minor consequences if not completed, 
3. C: Nice-to-do items with no significant consequence whether done or not,
4. D: Work that you can delegate to others,
5. E: Activities you should eliminate altogether.

{h3('When to use it')}

- For large and high-level backlogs (weekly TODOs, project plans, etc.),
- if you don't want to estimate each task at this stage,
- if you work in a team.

{h3('In practice')}

1. Decline calls and meetings in the first half of the day. Close your messenger, email, turn off the phone, etc. Your
productivity in the morning defines whether the rest of the day will succeed or fail. Doing the "complex task" in the 
afternoon is much, MUCH less efficient.

2. Your first and most important work item will take about three hours or 6 pomodoros. 
 * You aim at extracting maximum productivity from the morning session. The "big" item thus doesn't have to be specific 
 -- "Work on the bugs in Jira" would be a valid target, as long as you focus on it. 
 * Be realistic with the estimate for this session. On Monday you might be able to do 7 pomodoros, and on Friday -- 
 only 5. Don't overestimate it, since you still want to complete the remaining things on your list.
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

The 1-2-3, 3-3-3 and ABCD methods are very similar and focus on completing complex and unpleasant work first. They 
assume that *everything* that is planned needs to be done. This class of techniques should work best for the likes of 
software developers.

- 1-2-3 Rule only defines the number of tasks (just six for a day!) and is the simplest of the three.
- 3-3-3 Method prescribes the duration for the first task and has seven of them in total. It's a good choice if you 
tend to underestimate your work.
- ABCDE Method is the least prescriptive of the three, and helps you identify work that you can delegate to others or 
not do at all.

Other methods value simplicity, prioritize importance VS urgency, or focus on removing unnecessary work.

{h3('Key points')}

The key to making this ABCDE Method work is for you to now discipline yourself to start immediately on your "A" task. 
Stay at it until it is complete. Use your willpower to get going on this one job, the single most important task you 
could possibly be doing.

Eat the whole frog and don’t stop until it’s finished completely.

{h3('In practice')}

TO DO

{h3('See also')}

Details: [The ABCD List Technique for Setting Priorities](https://www.briantracy.com/blog/time-management/the-abcde-list-technique-for-setting-priorities/)

(C) Brian Tracy.

## A: A - Most important (significant consequences if not completed)

**"A" Items Are Most Important**

An A item is defined as something that is very important. This is something that you must do.

This is a task for which there can be serious consequences if you fail to do it. Consequences such as not visiting a key 
customer or not finishing a report for your boss that she needs for an upcoming board meeting.

These are the frogs of your life.

## B: B - Important (moderate consequences if not completed)

**"B" Items Only Have Minor Consequences**

A B item is defined as a task that you should do. But it only has mild consequences.

These are the tadpoles of your work life. This means that someone may be unhappy or inconvenienced if you don’t do it, 
but it is nowhere as important as an A task. Returning an unimportant telephone message or reviewing your email would be 
a B task.

The rule is that you should never do a B task when there is an A task left undone. You should never be distracted by a 
tadpole when there is a big frog sitting there waiting to be eaten.

## C: C - Nice to do (no significant consequence whether done or not)

**"C" Tasks Have No Consequences**

A C task is something that would be nice to do, but for which there are no consequences at all, whether you do it or 
not.

C tasks include phoning a friend, having coffee or lunch with a coworker or completing some personal business during 
work hours. This sort of activity has no effect at all on your work life.

As a rule, you can never complete a C task when there are B or A tasks left undone.

## D: D - Delegate (need to be done but not necessarily by you)

**"D" for Delegate**

A D activity is something that you can delegate to someone else.

The rule is that you should delegate everything that you possibly can to other people. This frees up more time for you 
to engage in your A activities. Your A tasks and their completion, largely determine the entire course of your career.

## E: E - Eliminate (offer no real value and can be removed)

**"E" for Eliminate**

An E activity is something that you should eliminate altogether.

After all, you can only get your time under control if you stop doing things that are no longer necessary for you to do.

-----------------------------------------------------------------------------------------------------------------------

# Eisenhower: Eisenhower Matrix

> *"I have two kinds of problems: the urgent and the important. The urgent are not important, and the important are never 
urgent."* - Dwight D. Eisenhower

TODO: Describe

- People instinctively tend to prioritize urgent items, which is rarely the right thing to do

- Eisenhower Matrix aims at distinguishing between the two

- Try it if you feel that you do too much fire fighting

{h3('When to use it')}

TODO

{h3('In practice')}

We tend to give our attention to urgent tasks at the expense of important tasks. Urgent tasks come in hot into our 
inboxes and scream loudly for resolution. They are almost always someone else's problem, given to us on a short time 
frame that amplifies their volume. It becomes a serious problem when we are *only* dealing with the urgent and not 
giving adequate time to the important things that sit there, quietly and patiently.

Being at the mercy of the latest-and-loudest is no way to live --- you're constantly putting out fires but never 
building anything, constantly dealing with other people's problems but never developing your professional self, slowly 
burning out from all the stress and never doing the things you know will be fulfilling.

{h3('See also')}

[The urgent and the important](https://www.rtalbert.org/blog-archive/index.php/2019/10/14/the-urgent-and-the-important)

(C) Robert Talbert, Ph.D.

## UI: Urgent and Important (with deadlines or consequences)

Tasks that are urgent and important are the highest priority and should be done ASAP. They are automatic candidates for 
the Most Important Thing (MIT) list for a given day.

Example: The professor's unit recommendation for Promotion happens to be due on Friday, so this is both urgent and 
important --- that's an MIT on my list for tomorrow and has a two-hour block in my calendar tomorrow morning all by 
itself.

## NUI: Not Urgent and Important (with unclear deadlines that contribute to long-term success)

Tasks that are important but not urgent come second. These need to be done; schedule time during the week to do them.

Example: Reading the article about the course redesign is important, but not urgent --- schedule one pomodoro during the 
week to read and take notes on it, and get it done this week.

## UNI: Urgent and Not Important (require your attention, but do not have deadlines or consequences)

Tasks that are urgent but not important are third. Delegate these if possible. Otherwise schedule time for them, but 
not at the expense of the important stuff.

For example, suppose I get an email from a student who's having trouble with their professor and wants an appointment 
this week. I need to act on this, but it is not something I would categorize as strategically important in the sense of 
serving a long-term goal. So it's "urgent but not important". I'll probably delegate this by telling the student to set 
up an appointment with me through our office staff.

## NUNI: Not Urgent and Not Important (unnecessary, distractions, and time-wasters)

Tasks that are neither urgent nor important get whatever time is left over. 

-----------------------------------------------------------------------------------------------------------------------

# Pareto: Pareto Principle

> *"If we double our time on our top 20 percent of activities, we can work a two-day week and achieve 60 percent more 
than now."*

- Focus on the 20 percent of activities that generate 80 percent of your successes.

- The 80/20 principle allows you to work less, live more, and be more effective.

- A shocking 80 percent of our activities at work are probably a waste of our energy and time.

{h3('When to use it')}

TODO

{h3('In practice')}

When we act less, we think more. And we think better. Most valuable creative ideas come to us when we are not hyper-busy 
or stressed, but in a calmer, more contemplative and receptive frame of mind.

The time we save by applying the 80/20 principle to our work tasks should NOT be reinvested in work. The point of this 
exercise is precisely to work less but smarter. The point is to free ourselves up to take breaks, to relax, to think, 
to just be, to connect with others, and to do more nourishing, energising, soul-soothing things – all the things that 
makes us feel alive and connected to our deeper purpose.

{h3('See also')}

[How to Work Less, Live More, and Be More Effective](https://www.psychologytoday.com/gb/blog/the-art-of-self-improvement/202312/work-less-live-more-and-be-more-effective)

(C) Anna Katharina Schaffner Ph.D.

## 20: 20% Effort, 80% Outcomes

Which of my work activities matters most? What are the 20 percent that leads to my successes?

## 80: 80% Effort, 20% Outcomes

Which of the non-generative activities can I minimize? Which activities can I say no to in the future?

-----------------------------------------------------------------------------------------------------------------------

# Buffett: Warren Buffett's 5/25 Rule

- TO DO

{h3('When to use it')}

This is similar to the Pareto Principle, but prescribes the number of tasks. It works best for strategic planning, 
monthly and weekly backlogs, etc.

{h3('In practice')}

- TO DO

{h3('See also')}

TO DO

## 5: Top-5 Tasks (focus)

## 20: Remaining 20 Tasks (eliminate)

-----------------------------------------------------------------------------------------------------------------------

# 333: 3-3-3 Method

> *"You almost certainly can't consistently do the kind of work that demands serious mental focus for more than about 
three or four hours a day."*

TODO

{h3('When to use it')}

- It works best if you can allocate 3 -- 4 hours of uninterrupted focused time in your day, ideally in the morning.

{h3('In practice')}

- It creates a structure for your workday and helps you decide when to do what. In the morning, spend 3 hours working 
on your most important task. Then in the afternoon, do the shorter tasks and the maintenance tasks. 

- It keeps us from falling behind on maintenance tasks.

This is not just a prioritization technique, but a method to structure your day.

{h3('See also')}

[The three-or-four-hours rule for getting creative work done](https://www.oliverburkeman.com/fourhours)

## 1: Most Important Thing (spend 3 hours on this)

## 2: Short Tasks (maximum 3)

## 3: Maintenance Activities (maximum 3)

-----------------------------------------------------------------------------------------------------------------------

# MSCW: MoSCoW Method

This method works well for prioritizing tasks within a project. You'd use it for organizing bigger backlogs.

{h3('When to use it')}

TODO

{h3('In practice')}

- Relative priorities within "should have" and "could have" classes affect decisions on trade-in and trade-out.

- It is important to distinguish between the "Must haves" and the rest, but less important to distinguish between 
"Should haves" and "Could haves". It is important to order tasks in the two middle sections.

- Should re-evaluate the items regularly.

{h3('See also')}

[MoSCoW method (Wikipedia)](https://en.wikipedia.org/wiki/MoSCoW_method)

[Fast-track: a RAD approach](https://archive.org/details/fasttrackradappr0000cleg/mode/2up)

(C) Dai Clegg

## M: M - Must have (failure if at least one is not done / without these, it is not worth delivering the project)

Requirements labelled as Must have are critical to the current delivery timebox in order for it to be a success. If even 
one Must have requirement is not included, the project delivery should be considered a failure (note: requirements can 
be downgraded from Must have, by agreement with all relevant stakeholders; for example, when new requirements are deemed 
more important). MUST can also be considered an acronym for the Minimum Usable Subset.

## S: S - Should have (important but not necessary / it is currently intended to deliver those as well)

Requirements labelled as Should have are important but not necessary for delivery in the current delivery timebox. While 
Should have requirements can be as important as Must have, they are often not as time-critical or there may be another 
way to satisfy the requirement so that it can be held back until a future delivery timebox.

## C: C - Could have (desirable but not necessary / if time allows some of thest may be delivered)

Requirements labelled as Could have are desirable but not necessary and could improve the user experience or customer 
satisfaction for a little development cost. These will typically be included if time and resources permit.

## W: W - Won't have (least-critical or not appropriate / the project will not deliver these)

Requirements labelled as Won't have, have been agreed by stakeholders as the least-critical, lowest-payback items, or 
not appropriate at that time. As a result, Won't have requirements are not planned into the schedule for the next 
delivery timebox. Won't have requirements are either dropped or reconsidered for inclusion in a later timebox. (Note: 
occasionally the term Would like to have is used; however, that usage is incorrect, as this last priority is clearly 
stating something is outside the scope of delivery). (The BCS in edition 3 & 4 of the Business Analysis Book describe 
'W' as 'Want to have but not this time around')

-----------------------------------------------------------------------------------------------------------------------

# MSW: Must, Should, Want

{h3('When to use it')}

It's a simplified version of the MoSCoW method, which works brilliantly for personal backlogs.

- Unlike techniques focused on sizing the tasks, this one focuses on perceived importance, which might be easier to 
evaluate in practice.

- It doesn't tell you what to do once you categorized the tasks.

{h3('In practice')}

This method is the easiest to categorize your tasks in practice.

It’s also helpful for budgeting. Before you get paid or go shopping, make a list of what you must buy, what you should 
buy, and what you want to buy. Even seeing it written out like that will help you make better purchasing decisions.

Spend a few minutes to review your previous day before planning the new one.

Try with only one task in each category -- the results might surprise you.

{h3('See also')}

[Get the Best Start](https://web.archive.org/web/20140507073715/http://www.jayshirley.com/blog/2014/3/31/best-start-of-the-day)

(C) Jay Shirley

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

# Jar: Pickle Jar Theory

> *There’s something about a nice crunchy pickle, isn’t there?*

{h3('When to use it')}

It's a fun view on the same technique as 1-2-3. The analogy works well for some people. If you find it silly -- choose
another prioritization technique.

{h3('In practice')}

TO DO

{h3('See also')}

[Time Management: The Pickle Jar Theory](https://alistapart.com/article/pickle/)

(C) Jeremy Wright

## Rocks: Rocks (big, important goals or tasks)

## Pebbles: Pebbles (urgent but non-essential tasks)

## Sand: Sand (small distractions and busywork)

## Water: Water (private life, downtime, or hobbies)

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


