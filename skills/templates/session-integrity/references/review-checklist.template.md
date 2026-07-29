# Consistency Review Checklist

<!-- AUTHORING NOTE: this is the checklist Phase 2 of SKILL.md runs against. Start with
     these generic categories and add your own as you discover new failure modes worth
     checking for every time, not just the time you first noticed them. -->

## Stale references

- [ ] Any count, date, or status mentioned in what this session touched: is it still accurate, or
      did something change elsewhere that makes it stale?
- [ ] Any file path or link referenced: does it still point to something that exists?

## Contradictions

- [ ] Does anything written this session conflict with your profile (voice, services, constraints)?
- [ ] Does anything written this session conflict with a decision already in your decision log?

## Propagation

- [ ] If this session changed a fact that appears in more than one place, did it update every
      place, or only the one it was directly working on?
- [ ] Is there a summary document (a dashboard, an index, a status tracker) that needs to reflect
      this session's change and doesn't yet?

## Voice

- [ ] If this session produced external-facing writing, does it pass the voice skill's self-audit?

## Claimed vs. actual

- [ ] Does anything this session claims is "done" have actual evidence of being done (a passing
      test, a merged change, a sent message), or is the claim resting on intention alone?

## Your own additions

<!-- AUTHORING NOTE: as you catch a new kind of mistake more than once, add a check for it here.
     This file should grow slowly over the life of your practice; a checklist that never changes
     usually means nobody's updating it after a miss, not that nothing's being missed. -->

- [ ] [Your own recurring check, added the first time you notice this pattern of mistake]
