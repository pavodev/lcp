# This file contains English translations for the LCP platform.


## --------------- GENERAL ---------------

platform-general = LiRI Corpus Platform
platform-general-short = LCP
platform-catchphrase = catchphrase
platform-soundscript = soundscript
platform-videoscope = videoscope
plaftorm-general-description =
    The LiRI Corpus Platform (LCP) is a software system for handling and querying corpora of different kinds. Users can query corpora directly from their browser, and upload their
    own corpora using a command-line interface.
platform-general-no-permission = You currently don't have permissions to query this corpus. Please see the corpus description to learn how to gain access.
platform-general-access-restricted = Access to this corpus is restricted. We need you to log in to evaluate your permissions.
platform-general-find-corpora = Find Corpora
platform-general-corpus-edit = Corpus edit
platform-general-corpus-license = Corpus licence
platform-general-user-license = Corpus licence: User defined - Check details
platform-general-corpus-details = Corpus details
platform-general-corpus-settings = Corpus settings
platform-general-corpus-origin = Corpus origin
platform-general-data-type = Data type

## --------------- COMMON ---------------

common-user =
    { $count ->
       *[one] User
        [other] Users
    }
common-name = Name
common-email = Email
common-admin = Admin
common-login = Login
common-logout = Logout
common-active = Active
common-ready = Ready
common-invited = Invited
common-invite = Invite
common-remove = Remove
common-key = Key
common-secret = Secret
common-help-1 = Your secret will not be visible after closing this window.
common-help-2 = The secret will be shown just once. Copy the secret to the safe place.
common-match = Match
common-details = Details
common-close = Close
common-stop = Stop
common-save = Save
common-submit = Submit
common-copy-clipboard = Copy to clipboard
common-loading = Loading
common-loading-data = Loading data
common-previous = Previous
common-next = Next
common-select-document = Select document
common-corpus = Corpus
load-example-query = Load example query
common-query-corpus = Query corpus
common-go-to-time = Go to time
common-loading-video-duration = Loading video duration
common-frame = Frame
common-time = Time
common-add-group = Add new group
common-group-settings = Group settings
common-start-date = Start date
common-finish-date = Finish date
common-institution = Institution
common-enabled = Enabled
common-disabled = Disabled
common-description = Description
common-partition = Partition
common-word-count = Word count
common-revision = Revision
common-play-audio = Play audio
common-play-video = Play video
common-zoom-out = Zoom Out
common-zoom-in = Zoom In
common-zoom-reset-default = Reset default
common-zoom-fit-content = Fit content

## --------------- MENU ---------------

menu-home = Home
menu-query = Query
menu-viewer = Viewer
menu-manual = Manual

## --------------- MODALS ---------------


# Corpus details modal

modal-details-count = Word count
modal-details-revison = Revison
modal-details-url = URL
modal-details-description = Description
modal-details-partitions = Partitions
modal-details-segments = Segments
modal-details-license = License
modal-details-user-license = User defined

# Metadata edit modal

modal-meta-name = Name
modal-meta-source = Source
modal-meta-authors = Authors
modal-meta-provider = Provider/Institution
modal-meta-revision = Revision
modal-meta-data-type = Data type
modal-meta-description = Description
modal-meta-license = License
modal-meta-user-defined = User defined
modal-meta-user-license = User defined license

# New/Edit project modal

modal-project-new = New Group
modal-project-title = Title
modal-project-title-error =
    Title is mandatory (min. length is seven letters).
    Title will be manually checked. Try to be concise and informative.
modal-project-start-date = Start date
modal-project-start-date-error = Start date is mandatory.
modal-project-end-date = End date
modal-project-end-date-error = End date is mandatory.
modal-project-description = Description
modal-project-description-placeholder = Please describe the purpose of your group
modal-project-tab-metadata = Metadata
modal-project-tab-permissions = Permissions
modal-project-tab-api = API
modal-project-data-public = Request to Make Data Public
modal-project-invitation = (invitation sent to { $email })
modal-project-invited = Invited users
modal-project-invite = Invite people
modal-project-invite-placeholder = Email (comma-separated list of email addresses)
modal-project-invite-help = Separate multiple email addresses with a comma.
modal-project-issued = Issued on
modal-project-revoke-key = Revoke API Key
modal-project-create-key = Create API Key

# Results details modal

modal-results-tab-graph = Dependency Graph
modal-results-tab-tabular = Tabular

# Results components

results-kwic-right-context = Right context
results-image-viewer = Image Viewer
results-audio-no-support = Your browser does not support the audio element.
results-plain-filter-placeholder = Filter by

# Footer

footer-report = Report a bug
