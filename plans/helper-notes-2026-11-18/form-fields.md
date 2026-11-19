# Form fields: BlueDot Rapid Grants, Manifund, Anthropic External Researcher Access

Looked up 2026-11-17. Read-only: nothing submitted, no accounts created, no sign-in, no email sent.

How each form was read (so you know how far to trust it):

- BlueDot: Airtable form, JavaScript-rendered, no login. I could not get the page to paint in a headless browser, so I read the form definition Airtable itself serves for the public page (the `readForPages` response for that form), which holds every field label, helper text, option list, required flag, visibility rule and validation rule in layout order. All fields visible: YES.
- Manifund: the create form is behind login (`/create` redirects to `/login`). I did NOT see it rendered. I read the form's source code in Manifund's public repo (github.com/manifoldmarkets/manifund, `app/create/create-project-form.tsx`, main branch, last changed 2026-10-14) and checked its Grantee FAQ source against the live FAQ page (identical). Labels, help text, required stars, limits and the description template come from that source. The live page could differ in small ways. All fields visible: NO (not rendered), but the source is complete.
- Anthropic: Google Form, no login to view, read from the form's own embedded definition. All fields visible: YES.

---

## 1. BlueDot Impact Rapid Grants

- Program page: https://bluedot.org/grants/rapid (same content at https://bluedot.org/programs/rapid-grants). Grants overview: https://bluedot.org/grants
- Form URL (Airtable, single page): https://airtable.com/appeeZXWP0NdMvWYd/paggDLIdBeveEPLs7/form
- Form published/last modified: 2026-11-16 (yesterday), so the wording is very recent.
- Form title: "Rapid Grant application"
- Form intro text: "You are applying for a Rapid Grant (https://bluedot.org/programs/rapid-grants). If you have any questions, email team@bluedot.org."
- After submit: "Thanks, we've received your application. You'll get a confirmation email shortly." (No "submit another response" option.)

### Stated terms (program page)

- Size: "Funding of up to $20,000 for time and resources to make progress on AI safety or biosecurity - from exploring a promising direction to carrying out a concrete project." Grant size "Up to $20k". (Larger: Seed Grants and Career Transition Grants are $20k to $200k.)
- Time to apply: about 15 minutes.
- Decision time: "On average we make a decision in 5 days." Apply any time (rolling).
- Payment: single lump sum after you submit a claim through BlueDot's claims portal and "any required checks"; transfer fees and exchange costs may reduce the amount received.
- What it funds: research and learning (time, living costs, research access); projects and experiments (compute, tools, testing an idea); events and community (meetups, venues); travel and collaboration (conferences, fieldwork). "We look for a worthwhile direction, evidence you can make progress, and a clear role for funding. Wildcards welcome. If in doubt, apply."
- Eligibility (verbatim): "People taking a promising next step in AI safety or biosecurity, subject to our funding restrictions. You're more likely to receive a grant if you're a BlueDot course participant, alumni, facilitator, or active member of the AI safety/biosecurity community." The grants overview page adds: "Do I need to have taken a BlueDot course? No. You do not need to have taken a BlueDot course to apply for any of our grants."
- Funding restrictions: cannot send money to Afghanistan, Belarus, Burundi, Central African Republic, Chad, China, Congo Republic, Cuba, Democratic Republic of the Congo, Eritrea, India, Iraq, Iran, Libya, Myanmar, North Korea, Somalia, South Sudan, Sudan, Syria, Russia, Venezuela, Yemen. "We cannot fund individuals or organizations where doing so would breach applicable sanctions." Unsure: contact BlueDot before applying.
- What it cannot fund: "party-political donations or campaigning, activities that are unlawful in the UK or your jurisdiction, or activities outside BlueDot's charitable or educational purposes. Funds must be used for the agreed purpose; material changes need our prior written approval."
- After the grant: short completion report within 60 days of finishing the work or the grant period ending.
- Individuals: yes, the form has an "Individual" recipient option and says "Choose Organization if you'd want the grant paid to a company, charity, university or fiscal sponsor rather than to you."
- For-profit: the program page does not mention for-profits. The form accepts "Company" as an organization type, so a company can be the payee. The charitable or educational purposes restriction above is the only related limit. BlueDot Impact is a UK CLG with a US 501(c)(3) arm (BlueDot Impact US Inc), which is why that wording is there.
- Location: no US restriction; only the sanctioned list above. Form asks "Where are you based?".
- AI use in writing the application: the page and form say nothing about it.

### Fields, in form order (single page, 23 user-facing fields plus 1 read-only)

Required means the form marks it required. Conditional fields are only shown when their rule is met.

1. **Your name** -- short text. Required. No helper text. (Underlying column "Full name".)
2. **Your email** -- short text with email validation. Required. No helper text.
3. **Where are you based?** -- short text. Required. Helper: "We cannot fund individuals or organizations where doing so would breach applicable sanctions or local laws."
4. **Where can we learn more about you?** -- long text (rich text). Required. Helper: "LinkedIn or personal website preferred. If this is to support an organization, please also add relevant links here."
5. **What are you requesting funding for?** -- short text, max 200 characters. Required. Helper: "The one sentence version, please!"
6. **How are you connected to the BlueDot community?** -- multi-select list. Required. Options: Course participant; Course alum; Facilitator; AI safety community member; Other.
7. **Are you currently enrolled in our Technical AI Safety Project Sprint?** -- checkbox. Optional. Conditional: shown only if #6 includes "Course participant".
8. **How much funding are you requesting?** -- number, currency USD, positive only, 2 decimals. Required. Helper: "Your best estimate, to the nearest $50."
9. **Tell us more about your project.** -- long text (rich text). Required. No helper text, no stated limit.
10. **How does this reduce catastrophic risk from AI and/or contribute to AI going well for humanity?** -- long text (rich text). Required. No helper text.
11. **What have you already done?** -- long text (plain). Required. Helper: "Describe concrete progress: code written, pilots run, drafts completed, data collected. If you haven't started, explain what you've done to validate the idea."
12. **What makes you think this project will be successful? Why you? Why now?** -- long text (plain). Required. No helper text.
13. **What specifically would this grant fund?** -- long text (rich text). Required. Helper: "List the specific items or services and estimated cost for each. Examples: "$200 Colab Pro+ (2 months), $150 Anthropic API credits for evaluation runs" · "$500 venue hire for 4 monthly meetups, $200 catering" · "$750 conference registration, $600 flights, $400 accommodation." If you are requesting stipend explain what you would be doing."
14. **What would you do without this grant?** -- long text (rich text). Required. Helper: "Would you abandon the project, reduce scope, use slower/free alternatives, or fund it yourself? What would the impact of this be?"
15. **Add any supporting links** -- long text (plain). Optional. Helper (from the field's description in the table, shown under the label): "Links to the project or supporting documents."
16. **How could we make this process better, or otherwise help you succeed with your project? Also add any other information you feel we should consider here.** -- long text (rich text). Optional. No helper text.
17. **Can we share your application with other funders and organizations as relevant?** -- single select. Required. Options: Yes; No. Pre-selected: Yes.
18. **If we approve your grant, can we share details about it publicly?** -- single select. Required. Options shown: Can share publicly with my name; Can share publicly without my name. (The column also has "Cannot share publicly" but the form hides it.) Pre-selected: "Can share publicly with my name".
19. **Public URL** (no custom label; field name shown) -- URL (short text with URL validation). Optional. Helper: "Provide one URL which we will link to on our website". Conditional: shown only if #18 is not "Cannot share publicly" (so effectively always visible).
20. **Who would we pay if your grant is approved?** -- single select. Required. Options: Individual; Organization. Helper: "Choose Organization if you'd want the grant paid to a company, charity, university or fiscal sponsor rather than to you." plus bold: "We can only pay grants to the individual or organization named in this application. If you aren't named, or authorized to act for a named organization, you won't be able to claim a successful grant."
21. **Organization's legal name** -- short text. Required when shown. Conditional: only if #20 = Organization. Helper: "If you are fiscally sponsored please write "Your Org/Project Title fiscally sponsored by "Your Fiscal Sponsor""
22. **What kind of organization is it?** -- single select. Required when shown. Conditional: only if #20 = Organization. Options: Company; Charity or nonprofit; University; Fiscal sponsor (hosts my project); Other. Helper: "If a fiscal sponsor or host will keep a fee, include it in your budget: it can only come out of the grant if we approve it."
23. **Which country is the organization registered in?** -- short text. Required when shown. Conditional: only if #20 = Organization. No helper text.
24. **Program** (read-only, pre-filled "Rapid Grants") -- linked-record card, cannot be edited by the applicant. Not a question.

No file upload field. No word limits stated anywhere except the 200-character cap on #5. No multi-page flow (one page).

### Eligibility points for a one-person US applicant, individual, with a for-profit LLC behind him

- No hard block found. US is not on the restricted country list. "Individual" is an explicit payee option.
- Choose payee carefully: if the LLC is paid, pick Organization / Company and you must fill #21 to #23 (legal name, type, country of registration). If paid personally, pick Individual and none of those show.
- Soft risk: grants cannot fund "activities outside BlueDot's charitable or educational purposes". A project that is mainly a commercial product for the LLC may be read as outside that. Frame it as research or a public-benefit output (this is my reading, the page does not say it).
- Soft risk: "more likely" for BlueDot community members. #6 asks for it and is required (pick "Other" or "AI safety community member" if true). Not a requirement.
- Payment only after a claims-portal step and "required checks" (likely identity and sanctions), and a completion report is due within 60 days.

---

## 2. Manifund: new project proposal (Technical AI safety)

- Entry points: https://manifund.org/create (needs login; redirects to https://manifund.org/login), https://manifund.org/about/open-call ("Funding Your Project on Manifund"), https://manifund.org/about/grantee-faq. Cause page: https://manifund.org/causes/tais (title "Technical AI safety").
- Form URL: https://manifund.org/create (single page, site-native, login required, created under "Publish project").
- Not seen rendered; fields below are from the open-source form code (see top of this file).

### How it works (open-call page, verbatim in substance)

1. Start a new project (Create).
2. Complete the proposal form: "Write up a description of your project and set parameters around the amount of funding you're trying to raise and the deadline for raising it."
3. Sign the grant agreement (legal paperwork, appears on the project page once published).
4. Receive funding: "If donors collectively offer your project the minimum funding amount you specify before the deadline, then you'll receive payment through Manifund to start your project!"
- "Anyone can create a public proposal on Manifund for grant funding." Causes listed: Science & technology, Technical AI safety, Biomedical, AI governance, Animal welfare, Biosecurity, EA community, Forecasting, Global catastrophic risks, Global health & development, AI safety fieldbuilding, AI safety advocacy, Digital minds, Epistemics. "However, you're welcome to submit an application for any public-benefit project, as long as it meets legal requirements about what we can fund as a 501(c)(3)."
- Publishing is public immediately. FAQ "A note for AIs": post publicly rather than emailing questions first; "Posting doesn't commit you to anything, and you can put any open questions and caveats in the proposal itself." Manifund cannot give feedback on drafts before posting.

### Grantee FAQ, verbatim answers that matter

- Eligible project: "Any project with a charitable purpose can be posted on Manifund. That doesn't mean the project will get funded: that depends on whether donors on Manifund choose to recommend grants to it."
- Who can receive a grant: "Individuals: Manifund provides model C fiscal sponsorship. Nonprofits. For-profits, as long as the grant is for a charitable purpose. Grantees outside the US: we can pay individuals and organizations in most countries by international wire."
- Minimum size: "Manifund has a minimum project size of $500. Consider other sources like BlueDot Rapid Grants for smaller amounts."
- AI writing: "Yes [you can use AI], but we use Pangram to check proposals and it will be flagged with a banner saying 'Likely AI-generated,' making donors less likely to read it." The score is recomputed on every edit. The form itself warns: "We recommend writing your proposal in your own words, rather than with an AI; the home page filters out projects that are flagged as AI-written."
- Fees: none on grantees; donors who have given more than $50k in total pay 5%.
- Friends and family may make funding offers but must disclose conflicts, which Manifund reviews before approving.
- Time to a decision: no stated review time. The funding window is set by the applicant (see deadline field).

### Fields, in form order

Required marked with a star in the form.

0. (Only appears if a special funding round with a prize is open, or via a `?prize=` link) **I am applying for...** -- radio. Options: "A regular grant" (default) plus any open round titles. Helper: "Learn more about different funding rounds here." For a normal AI safety grant choose "A regular grant". Not a question you need to answer otherwise.

Section "New proposal":

1. **Title** -- short text. Required. Max 80 characters (counter shown "n/80 characters").
2. **Subtitle** -- short text. Optional. Max 160 characters.
3. **Project description** -- rich text editor. Required. Help tooltip: "Use bullet points, headings, hyperlinks and more. Use Notion-style markdown shortcuts or paste from Google Docs." Amber notice: "We recommend writing your proposal in your own words, rather than with an AI; the home page filters out projects that are flagged as AI-written." No word or character limit stated. Pre-filled with this standard template (each is an H3 heading, in this order, with no guidance text under it):
   1. Project summary
   2. What are this project's goals? How will you achieve them?
   3. How will you know it worked?
   4. How will this funding be used?
   5. Who is on your team? What's your track record on similar projects?
   6. What are the most likely causes and outcomes if this project fails?
   7. How much money have you raised in the last 12 months, and from where?
   (A "Reset" control restores the template. A draft is saved in the browser.)

Section "Funding":

4. **Minimum funding (USD)** -- number. Required. Help tooltip: "The minimum amount of funding you need to start this project. If this amount is not reached, no funds will be sent. Due to the cost of approving grants and processing payments, we require this to be at least $500." Error if under $500: "Minimum funding must be at least $500." Placeholder 500.
5. **Max funding goal (USD)** -- number. Required. Help tooltip: "Until this amount is raised, the project will be marked for donors as not fully funded. If this amount is different from your minimum funding, please explain in your project description what you could accomplish with the minimum funding and what you could accomplish with the full funding." Must be greater than 0 and at least the minimum: "Funding goal must be greater than 0 and greater than or equal to your minimum funding." No stated maximum.
6. **Decision deadline** -- date picker. Required. Help tooltip: "After this deadline, if you have not reached your minimum funding bar, your application will close and you will not receive any money. This date cannot be more than 6 weeks after posting." Default is 1 month from today. Error: "Your application close date must be in the future but no more than 6 weeks from now."

Section "Logistics":

7. **Cause areas** -- multi-select picker of causes (select "Technical AI safety"; more than one allowed, e.g. AI safety fieldbuilding, AI governance, Science & technology). Optional in the code (no star).
8. **What countries are you (and anyone else working on this) based in?** -- short text. Required. Helper: "This is for Manifund operations and will not be published." Error if empty: "Please specify the location of your project."
9. **This project will engage in lobbying.** -- checkbox (link to IRS lobbying definition). Optional. Tooltip: "Check this box if you will use this money to lobby (attempt to influence legislation, as defined by the IRS), within the US or internationally."
10. Button: **Publish project** (disabled until title, minimum funding, funding goal, deadline and location are valid).

After publishing: a grant agreement to sign on the project page; funding requirements shown on the project include "Sign grant agreement", "Reach min funding", "Get Manifund approval" (seen on a live example). A Manifund account is needed (login) before the form opens.

### Funding window summary

- Minimum funding: at least $500, required, you set it. Funds are paid only if donors collectively reach it before the deadline.
- Max funding goal: required, at least the minimum, you set it. Marks "fully funded" status only.
- Deadline: required, you pick a date, between tomorrow and 6 weeks after posting (default 1 month). If minimum is not reached by then the application closes and nothing is paid. No separate review period is stated; donors and regrantors can fund at any time before the deadline, and Manifund approves the grant at the end ("Get Manifund approval").

### Eligibility points for a one-person US applicant, individual, with a for-profit LLC behind him

- No hard block. Individuals are explicitly supported (Manifund acts as fiscal sponsor, "model C"). For-profits are explicitly allowed "as long as the grant is for a charitable purpose". So both the individual and the LLC route are open; the project must be a public-benefit one (the 501(c)(3) rule), which AI safety research normally is. A purely commercial product would not fit.
- Real risk is not eligibility, it is funding: nothing is paid unless donors reach the minimum inside the 6-week window.
- If the proposal text is flagged "Likely AI-generated" donors are less likely to read it, and the home page filters those out.

---

## 3. Anthropic External Researcher Access Program

- Program page: https://support.claude.com/en/articles/9125743-what-is-the-external-researcher-access-program (the same article exists on support.anthropic.com; "March 16, 2026" on the page).
- Form URL (Google Form, single page, no login to view): https://forms.gle/pZYC8f6qYqSKvRWn9 (edit-link version also referenced: https://docs.google.com/forms/d/1O2Om9t4CQoLKHQew7XguQYKrPGS8-sCmK42KNXcwn3k)
- Form title: "Application Form - Anthropic's External Researcher Access Program"

### Stated terms

- Credit: "If successful, we will apply $1000 API credits to the account. For rare special cases, we may approve a higher quantity of credits." (help article: "$1000 in API credits".) The form asks if you want more than $1000 and lets you type an amount.
- Review cadence: "We evaluate submissions on the first Monday of each month." (Today is Tue 2026-11-17, so the next review is Monday 2026-12-07.) "If this timeline poses a significant obstacle for the applicant, it does not block them from simply purchasing API credits in the interim."
- No individual replies to unapproved submissions ("in the thousands" of applications; "we reserve the right to reject submissions for any reason"). Help article adds: "sometimes thousands in a single week". Urgent issues: researcheraccess@anthropic.com.
- Purpose: "free API credits ... to researchers working on AI safety and alignment topics we consider high priority."
- Eligibility, as stated: "If you are an alignment researcher and are interested in receiving free API credits for AI safety and alignment research purposes, you might qualify." No other formal criteria (no institution, degree, citizenship or location requirement). The form takes "individual applicant or team" and the organization name is optional, so individuals are fine.
- For-profit applicants: not addressed on the page or form. (Nothing says a company or LLC is excluded.) Tax question only asks if you are in the US.
- Credits are for the API only (not Claude.ai), cover the standard model suite, no nonpublic or experimental models, no finetuning via API. Applicants "do not receive exemption from our Usage Policy" (red-teaming gets no exemption unless you collaborate with an Anthropic employee who starts an internal approval). Multi-person programs: one account, one application, credits go to a single Console organization ID.
- You need a Claude Console account and its Organization ID before applying: "If you have not yet set up an account, please set up an account at https://console.anthropic.com before submitting this form."
- AI use in writing the application: not mentioned.
- Confidentiality: "Anthropic treats information submitted through this form as non-confidential or proprietary, so please do not submit confidential or proprietary information in your proposal."
- The Google Form showed no sign-in requirement and no file upload field.

### Fields, in form order (one page, 13 items)

1. **Name of primary contact** -- short text. Required.
2. **Name of organization (if applicable)** -- short text. Optional.
3. **Have you been recommended to this form by an Anthropic employee?** -- single choice. Required. Options: Yes; No.
4. **If you have been referred to this form by an Anthropic employee, please enter their name here:** -- short text. Optional.
5. **Which Organization ID would you like the credits applied to?** -- short text. Required. Helper: "Note: this can be found under https://console.anthropic.com/settings/organization. It will look something like: 1bc14c5d-6442-4fa9-bgjj-c1ejei29aef01v. If you have not yet set up an account, please set up an account at https://console.anthropic.com before submitting this form."
6. **In less than 200 words, please provide a brief description of the individual applicant or team, including the relevant expertise.** -- long text. Required. Limit: 200 words (stated in the label; not enforced by the form).
7. **In less than 300 words, please describe your research or request for free API credits, making sure to explain:** "- The topic of the project or research" and "- Why free API credits are important for your team to complete this research/project" -- long text. Required. Limit: 300 words (stated in the label).
8. **Are you requesting more than $1000 API credits? If so, please enter the amount in 'Other'** -- single choice with an "Other" free-text. Required. Options: No; Other (type the amount).
9. **In order to keep this free program sustainable to run, we prefer to have these accounts set to a 'low quality of service' where possible, meaning that in the event that we run out of capacity, these accounts would receive the errors first. Would this be a significant hindrance for your research / use case? Please choose below:** -- single choice. Optional. Options: "I'm fine with receiving a low quality of service"; "My use case will require a standard quality of service".
10. **Please provide a link to your Google Scholar profile or github profile:** -- long text (paragraph box, used for a URL). Required.
11. **Additional Information: Please provide any additional context or considerations for the review committee (Optional)** -- long text. Optional.
12. **Are you located within the United States? (This question is for our tax & accounting purposes)** -- single choice. Optional. Options: Yes; No.
13. **Terms of Service:** "Anthropic treats information submitted through this form as non-confidential or proprietary, so please do not submit confidential or proprietary information in your proposal. By submitting information through this form, you agree to Anthropic's Terms of Service. Personal information you submit will be handled in accordance with our Privacy Policy. If you would like to request deletion of your information, please reach out to researcheraccess@anthropic.com." -- checkbox. Required. Option: I agree.

Form intro text (above the fields): "Thank you for your interest in Anthropic's External Researcher Access Program. Please complete the following application form with details about your team and research topic." then "About this Program" (free API credits for the standard model suite for safety and alignment research topics "we consider high priority"; API only; no non-public models; no Usage Policy exemption; if collaborating with an Anthropic employee and needing an exemption, tell that employee), and "About our Process" (first Monday of each month; $1000; no individual responses to unapproved submissions).

### Eligibility points for a one-person US applicant, individual, with a for-profit LLC behind him

- No hard block found. Individuals are an explicit applicant type. US location is only for tax. For-profit status is not mentioned.
- Credits go to a Console organization ID, so the LLC's or the individual's Console org can be used; the form does not say which is preferred.
- The application must show alignment or safety research (relevant expertise plus a Scholar or GitHub link are required fields). Credits are small ($1000 unless you request and justify more) and the monthly review means the next decision day is 2026-12-07.
- Not a block but worth knowing: the content is treated as non-confidential, there is no feedback if rejected, and the program gives no Usage Policy exemption (relevant for red-team style research such as adversarial prompts against models).
