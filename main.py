package com.example.ui.screens

import android.content.Intent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Sort
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.font.FontWeight
import com.example.data.*
import com.example.ui.theme.*
import kotlinx.coroutines.launch

enum class FeedSortOption(val label: String, val description: String) {
    DATE_UPLOADED("Date Uploaded", "Chronological by upload date"),
    NEWEST("Newest", "Newest uploads first"),
    OLDEST("Oldest", "Earliest uploads first")
}

fun formatPostDate(timestamp: Long): String {
    val now = System.currentTimeMillis()
    val diff = (now - timestamp).coerceAtLeast(0)
    return when {
        diff < 60_000L -> "Just now"
        diff < 3600_000L -> "${(diff / 60_000L).coerceAtLeast(1)}m ago"
        diff < 86400_000L -> "${diff / 3600_000L}h ago"
        diff < 7 * 86400_000L -> "${diff / 86400_000L}d ago"
        else -> {
            val sdf = java.text.SimpleDateFormat("MMM d, yyyy", java.util.Locale.getDefault())
            sdf.format(java.util.Date(timestamp))
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FeedScreen(
    repository: PikDRepository,
    onCreatePostClick: () -> Unit,
    onAuthRequired: () -> Unit
) {
    val posts by repository.posts.collectAsState()
    val likedIds by repository.likedPostIds.collectAsState()
    val savedIds by repository.savedPostIds.collectAsState()
    val commentsMap by repository.comments.collectAsState()
    val profile by repository.profile.collectAsState()
    val settings by repository.settings.collectAsState()
    val isLoggedIn by repository.isLoggedIn.collectAsState()

    var isRefreshing by remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()
    val pullToRefreshState = rememberPullToRefreshState()

    var selectedSortOption by remember { mutableStateOf(FeedSortOption.NEWEST) }
    var sortMenuExpanded by remember { mutableStateOf(false) }

    val sortedPosts = remember(posts, selectedSortOption) {
        when (selectedSortOption) {
            FeedSortOption.DATE_UPLOADED -> posts.sortedByDescending { it.createdAt }
            FeedSortOption.NEWEST -> posts.sortedByDescending { it.createdAt }
            FeedSortOption.OLDEST -> posts.sortedBy { it.createdAt }
        }
    }

    PullToRefreshBox(
        isRefreshing = isRefreshing,
        onRefresh = {
            coroutineScope.launch {
                isRefreshing = true
                repository.syncLatestMediaFromServer()
                isRefreshing = false
            }
        },
        state = pullToRefreshState,
        modifier = Modifier.fillMaxSize().background(CyberBg)
    ) {
        Column(modifier = Modifier.fillMaxSize().background(CyberBg)) {
            // Sort Dropdown Header Bar
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Sort,
                        contentDescription = "Sort feed",
                        tint = CyberCyan,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "MEDIA FEED",
                        color = CyberWhite,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.ExtraBold,
                        letterSpacing = 1.sp
                    )
                    if (sortedPosts.isNotEmpty()) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(CyberPanelBorder)
                                .padding(horizontal = 6.dp, vertical = 2.dp)
                        ) {
                            Text(
                                text = "${sortedPosts.size}",
                                color = CyberCyan,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                // Interactive Dropdown Menu button
                Box {
                    Row(
                        modifier = Modifier
                            .clip(RoundedCornerShape(16.dp))
                            .background(CyberPanel)
                            .border(1.2.dp, CyberCyan.copy(alpha = 0.6f), RoundedCornerShape(16.dp))
                            .clickable { sortMenuExpanded = true }
                            .padding(horizontal = 12.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Sort: ${selectedSortOption.label}",
                            color = CyberCyan,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Icon(
                            imageVector = Icons.Default.ArrowDropDown,
                            contentDescription = "Open sort dropdown menu",
                            tint = CyberCyan,
                            modifier = Modifier.size(18.dp)
                        )
                    }

                    DropdownMenu(
                        expanded = sortMenuExpanded,
                        onDismissRequest = { sortMenuExpanded = false },
                        modifier = Modifier
                            .background(CyberPanel)
                            .border(1.dp, CyberPanelBorder, RoundedCornerShape(12.dp))
                    ) {
                        FeedSortOption.values().forEach { option ->
                            DropdownMenuItem(
                                text = {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        if (selectedSortOption == option) {
                                            Icon(
                                                imageVector = Icons.Default.Check,
                                                contentDescription = "Selected",
                                                tint = CyberCyan,
                                                modifier = Modifier.size(16.dp)
                                            )
                                            Spacer(modifier = Modifier.width(8.dp))
                                        } else {
                                            Spacer(modifier = Modifier.width(24.dp))
                                        }
                                        Column {
                                            Text(
                                                text = option.label,
                                                color = if (selectedSortOption == option) CyberCyan else CyberWhite,
                                                fontWeight = if (selectedSortOption == option) FontWeight.Bold else FontWeight.Normal,
                                                fontSize = 14.sp
                                            )
                                            Text(
                                                text = option.description,
                                                color = CyberGrey,
                                                fontSize = 11.sp
                                            )
                                        }
                                    }
                                },
                                onClick = {
                                    selectedSortOption = option
                                    sortMenuExpanded = false
                                }
                            )
                        }
                    }
                }
            }

            // Feed List
            LazyColumn(
                modifier = Modifier.fillMaxSize().background(CyberBg),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                items(sortedPosts, key = { it.id }) { post ->
                    PostCard(
                        post = post,
                        isLiked = likedIds.contains(post.id),
                        isSaved = savedIds.contains(post.id),
                        commentCount = (commentsMap[post.id] ?: emptyList()).size,
                        displayMode = profile.displayMode,
                        autoplay = settings.autoplayVideos,
                        accentColor = if (settings.showPostColours) getUniqueAccent(post.id) else CyberCyan,
                        onLikeClick = { if (isLoggedIn) repository.toggleLike(post.id) else onAuthRequired() },
                        onCommentClick = { if (isLoggedIn) { /* comment */ } else onAuthRequired() },
                        onShareClick = { /* share */ },
                        onSaveClick = { repository.toggleSave(post.id) },
                        onOptionsClick = { /* options */ }
                    )
                }
            }
        }
    }
}
